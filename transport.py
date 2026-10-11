"""Explicit Wi-Fi selection for the pinned pymobiledevice3 11.26.0 tunnel.

The upstream userspace handle manages lifecycle and transport-loss cleanup, but
its provider selector first asks usbmux. Temporarily inject the Wi-Fi provider
during opening only. Larp Studio permits one device job at a time; never auto-fallback
to USB, since that would falsely report a cable-independent connection.
"""
import asyncio
from contextlib import asynccontextmanager


@asynccontextmanager
async def open_tunnel(udid, connection="usb"):
    import pymobiledevice3.remote.userspace_tunnel as userspace
    from pymobiledevice3.remote.tunnel_service import get_remote_pairing_tunnel_services

    handle = userspace.UserspaceRsdTunnel(serial=udid, autopair=False, remotepairing_fallback=False)
    if connection == "usb":
        async with handle as rsd:
            if rsd.udid != udid:
                raise RuntimeError("Die Gerätekennung der Sitzung stimmt nicht überein.")
            yield rsd
        return
    if connection != "wifi":
        raise ValueError("Unbekannte Verbindungsart.")

    async def provider(serial, autopair, remotepairing_fallback):
        if serial != udid or autopair:
            raise RuntimeError("Ungültige WLAN-Geräteauswahl.")
        services = await get_remote_pairing_tunnel_services(udid=udid, bonjour_timeout=5)
        if not services:
            raise RuntimeError("iPhone im WLAN nicht gefunden. Gleiches WLAN nutzen, iPhone entsperren und WLAN zunächst per USB vorbereiten. Kein Gastnetz verwenden.")
        selected = services[0]
        try:
            for extra in services[1:]:
                await extra.close()
        except BaseException:
            await selected.close()
            raise
        return selected, None

    original = userspace._create_no_root_tunnel_provider
    try:
        userspace._create_no_root_tunnel_provider = provider
        try:
            rsd = await asyncio.wait_for(handle.aopen(), timeout=30)
        except asyncio.TimeoutError as exc:
            raise RuntimeError("Die WLAN-Verbindung hat nicht geantwortet. Gleiches WLAN und Windows-Firewall für private Netzwerke prüfen.") from exc
        finally:
            userspace._create_no_root_tunnel_provider = original
        if rsd.udid != udid:
            raise RuntimeError("Die WLAN-Gerätekennung stimmt nicht mit deinem iPhone überein.")
        yield rsd
    finally:
        await handle.aclose()


async def probe_wifi(udid):
    from pymobiledevice3.services.dvt.instruments.dvt_provider import DvtProvider
    async with open_tunnel(udid, "wifi") as rsd:
        async with DvtProvider(rsd):
            pass  # Establish developer services without changing the location.


async def clear_wifi(udid):
    from pymobiledevice3.services.dvt.instruments.dvt_provider import DvtProvider
    from pymobiledevice3.services.dvt.instruments.location_simulation import LocationSimulation
    async with open_tunnel(udid, "wifi") as rsd:
        async with DvtProvider(rsd) as dvt, LocationSimulation(dvt) as location:
            await asyncio.wait_for(location.clear(), timeout=10)
