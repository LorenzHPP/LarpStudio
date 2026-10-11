"""Browser checks with local fixtures; start app.py --preview before running."""
import argparse
import base64
from pathlib import Path
import struct
import tempfile
from playwright.sync_api import sync_playwright, expect

parser = argparse.ArgumentParser()
parser.add_argument('--url', default='http://127.0.0.1:8765')
parser.add_argument('--screenshot')
args = parser.parse_args()
errors = []
with sync_playwright() as p, tempfile.TemporaryDirectory() as scratch:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
    context = browser.new_context(viewport={'width':1440, 'height':940}, accept_downloads=True)
    context.route('https://tile.openstreetmap.org/**', lambda route: route.fulfill(content_type='image/svg+xml', body='<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256"><rect width="256" height="256" fill="#ddd"/></svg>'))
    page = context.new_page(); page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(args.url, wait_until='networkidle')
    expect(page.locator('html')).to_have_attribute('lang', 'en')
    expect(page.locator('.brand')).to_have_text('larp studio')
    page.locator('#artworkTab').click()
    expect(page.locator('#artworkWorkspace')).to_be_visible()
    expect(page.locator('#locationWorkspace')).not_to_be_visible()
    page.locator('[data-template=lines]').click()
    page.locator('#artworkTitle').fill('LARP STUDIO')
    page.locator('#artworkCaption').fill('MADE BY YOU')
    before = page.evaluate("document.getElementById('artworkCanvas').toDataURL()")
    page.locator('#artworkTitle').press('Enter')
    assert page.evaluate('state.phase') == 'disconnected', 'Artwork keyboard shortcut must not start a GPS session'
    if args.screenshot:
        page.screenshot(path=args.screenshot)
    with page.expect_download() as exported:
        page.locator('#exportArtwork').click()
    download = exported.value; download.save_as(str(Path(scratch) / 'card.png'))
    png = (Path(scratch) / 'card.png').read_bytes()
    assert png[:8] == b'\x89PNG\r\n\x1a\n' and struct.unpack('>II', png[16:24]) == (1536,969)
    assert base64.b64decode(before.split(',')[1]) == png
    # Build an image with a different aspect ratio, then import, zoom and drag.
    image_url = page.evaluate("""() => { const c=document.createElement('canvas');c.width=2000;c.height=900;const x=c.getContext('2d');x.fillStyle='#555';x.fillRect(0,0,2000,900);x.fillStyle='#eee';x.fillRect(200,0,450,900);return c.toDataURL(); }""")
    image = Path(scratch) / 'photo.png'; image.write_bytes(base64.b64decode(image_url.split(',')[1]))
    page.locator('#artworkImage').set_input_files(str(image))
    expect(page.locator('#artworkImageControls')).to_be_visible()
    page.locator('#artworkZoom').fill('1.4')
    original = page.evaluate("document.getElementById('artworkCanvas').toDataURL()")
    box = page.locator('#artworkCanvas').bounding_box()
    page.mouse.move(box['x']+150, box['y']+150); page.mouse.down(); page.mouse.move(box['x']+250, box['y']+150); page.mouse.up()
    assert page.evaluate("document.getElementById('artworkCanvas').toDataURL()") != original
    page.locator('#artworkRemoveImage').click()
    expect(page.locator('#artworkImageControls')).not_to_be_visible()
    assert page.evaluate("document.getElementById('artworkCanvas').toDataURL()") == before
    for w,h in [(1024,700),(1366,768)]:
        page.set_viewport_size({'width':w,'height':h})
        assert page.evaluate('document.documentElement.scrollWidth') == w
        page.locator('#exportArtwork').scroll_into_view_if_needed()
        b=page.locator('#exportArtwork').bounding_box(); assert b['y']>=60 and b['y']+b['height']<=h
    page.locator('#locationTab').click()
    page.locator('[data-mode=walk]').click(); page.evaluate('setPoint([47.631,9.911])')
    page.locator('#saveRoute').click(); page.locator('#savedRouteName').fill('<b>Meine Runde</b>')
    page.locator('#saveRouteForm button[type=submit]').click()
    expect(page.locator('#saveRouteDialog')).not_to_be_visible()
    page.reload(wait_until='networkidle')
    page.locator('[data-mode=walk]').click(); page.locator('#openRoutes').click()
    expect(page.locator('#savedRouteList')).to_contain_text('<b>Meine Runde</b>')
    assert page.locator('#savedRouteList b').count()==0
    page.locator('.saved-route-load').click()
    assert page.locator('.waypoint').count()==2 and page.evaluate('planned.length')==0
    page.wait_for_function("""() => waypoints.every(({point}) => {
        const p = map.latLngToContainerPoint(point);
        const panel = document.querySelector('.sidebar').getBoundingClientRect();
        return p.x > panel.right + 12 && p.x < map.getSize().x - 55
            && p.y > 100 && p.y < map.getSize().y - 95;
    })""")
    assert page.locator('#startButton').is_disabled()
    page.locator('#openRoutes').click(); page.locator('.saved-route-row .icon-button').click()
    expect(page.locator('#savedRouteList')).to_contain_text('No saved routes')
    page.locator('#routeLibraryDialog .close-dialog').click()
    # Native bridge: image export and persistent route storage use actual APIs, not a browser-only download.
    native=context.new_page(); native.on('pageerror', lambda error:errors.append(str(error)))
    native.add_init_script("""
      window.exports=[];window.routeStore=[];
      window.pywebview={api:{get_state:async()=>({ok:true,data:{phase:'disconnected',message:'TESTDATEN',logs:[],favorites:[]}}),
      get_routes:async()=>({ok:true,data:window.routeStore}),save_routes:async r=>{window.routeStore=r;return {ok:true,data:r}},
      save_artwork:async d=>{window.exports.push(d);return {ok:true,data:{saved:true}}}}};
    """)
    native.goto(args.url,wait_until='networkidle'); native.locator('#artworkTab').click(); native.locator('#exportArtwork').click()
    expect(native.locator('#toast')).to_contain_text('saved as PNG')
    assert len(native.evaluate('window.exports'))==1
    native.locator('#locationTab').click(); native.locator('[data-mode=walk]').click(); native.evaluate('setPoint([47.631,9.911])')
    native.locator('#saveRoute').click(); native.locator('#savedRouteName').fill('Native route'); native.locator('#saveRouteForm button[type=submit]').click()
    expect(native.locator('#saveRouteDialog')).not_to_be_visible()
    assert len(native.evaluate('window.routeStore'))==1
    assert not errors, errors
    browser.close()
print('PASS: artwork templates, exact PNG export, image import/crop/zoom/remove, shortcuts, minimum window, saved route load/delete/restart, native export and route bridge. No iPhone.')
