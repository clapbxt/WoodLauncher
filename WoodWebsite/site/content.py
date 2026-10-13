"""Page copy and a small renderer for the shared, plain Markdown mod guide."""
import html
import re


def render_guide(text):
    """Render headings, paragraphs, lists and fences used in docs/MODDING.md."""
    def inline(value):
        parts = re.split(r'(`[^`]+`)', value)
        return ''.join('<code>' + html.escape(part[1:-1]) + '</code>'
                       if part.startswith('`') and part.endswith('`')
                       else html.escape(part) for part in parts)

    result, paragraph, listing, fence = [], [], None, None
    code = []

    def flush():
        if paragraph:
            result.append('<p>' + inline(' '.join(paragraph)) + '</p>')
            paragraph.clear()

    def close_list():
        nonlocal listing
        if listing:
            result.append('</' + listing + '>')
            listing = None

    for line in text.splitlines():
        if line.startswith('```'):
            flush(); close_list()
            if fence is None:
                fence = line[3:]
                code = []
            else:
                value = '\n'.join(code)
                if fence == 'text':
                    result.append('<div class="actions"><button class="btn" type="button" id="copy-prompt">Copy AI prompt</button><a class="btn secondary" href="downloads/wood-mod-prompt.txt" download>Download prompt</a><span id="copy-status" role="status"></span></div>')
                result.append('<pre><code' + (' id="ai-prompt"' if fence == 'text' else '') + '>' + html.escape(value) + '</code></pre>')
                fence = None
            continue
        if fence is not None:
            code.append(line)
            continue
        if not line.strip():
            flush(); close_list(); continue
        heading = re.match(r'^(#{1,3}) (.+)$', line)
        if heading:
            flush(); close_list()
            if heading[1] == '#':
                continue  # The page shell already supplies h1.
            anchor = re.sub(r'[^a-z0-9]+', '-', heading[2].lower()).strip('-')
            result.append(f'<h{len(heading[1])} id="{anchor}">{inline(heading[2])}</h{len(heading[1])}>')
            continue
        item = re.match(r'^(?:- |\d+\. )(.+)$', line)
        if item:
            flush()
            kind = 'ul' if line.startswith('- ') else 'ol'
            if kind != listing:
                close_list(); listing = kind; result.append('<' + kind + '>')
            result.append('<li>' + inline(item[1]) + '</li>')
        else:
            close_list(); paragraph.append(line)
    flush(); close_list()
    if fence is not None:
        raise ValueError('Unclosed guide code fence')
    headings = re.findall(r'^## (.+)$', text, re.M)
    links = ''.join('<li><a href="#' + re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
                    + '">' + html.escape(title) + '</a></li>' for title in headings)
    return '<nav class="guide-toc" aria-label="On this page"><ol>' + links + '</ol></nav>\n' + '\n'.join(result)


HOME = '''<section class="hero"><div><p class="eyebrow">TUNG mod loader</p><h1>Load mods.<br><span>Make your own.</span></h1><p class="lede">Wood loads your mods and gives them an in-game menu. Install it once, then add the mods you want.</p><div class="actions"><a class="btn" href="downloads.html">Download Wood ↓</a><a class="btn secondary" href="mods.html">Browse mods ↗</a></div><p class="micro">Windows x64 · Version 1.1.4 · Updates automatically</p></div>{demo}</section><section class="section"><h2>Get started</h2><div class="steps"><div><div class="stepno">01 / INSTALL WOOD</div><h3>Run one installer.</h3><p>Close TUNG, run the Wood installer, and choose your TUNG folder.</p></div><div><div class="stepno">02 / ADD MODS</div><h3>Drop mods in.</h3><p>Download mods separately and put their .tungmod files in the Mods folder.</p></div><div><div class="stepno">03 / PLAY</div><h3>Launch TUNG.</h3><p>Wood updates at game startup. Press F10 to open the mod menu.</p></div></div></section><section class="closing"><div><h2>Build your first mod.</h2><p>Start with working Lua, Wood’s API, and a prompt for your AI.</p></div><a class="btn" href="developers.html">Make a mod →</a></section>'''

GUIDES = '''<h2 id="install">Install Wood</h2><ol><li>Install and launch TUNG through Steam once, then close it.</li><li><a href="downloads.html">Download the Wood installer</a>, run it, and choose the TUNG folder containing <code>TUNG.exe</code>.</li><li>Launch TUNG through Steam. Wood checks for updates at game startup; press <kbd>F10</kbd> to open its menu.</li></ol><p>The installer includes the runtime, updater, and uninstaller. No separate launcher app, Python installation, or Steam launch-option change is needed.</p><h2 id="mods">Add or remove mods</h2><ol><li><a href="mods.html">Download a mod</a> separately.</li><li>Copy its <code>.tungmod</code> package into the top-level <code>Mods</code> folder beside <code>TUNG.exe</code>. Create the folder if needed.</li><li>Restart TUNG. Press F10 and select the mod to open its settings.</li></ol><p>Keep one copy of each mod. To remove it, close TUNG, move its file out of Mods, and restart. To disable loading, put its filename without <code>.lua</code> (or its package ID) on a separate line in <code>.wood/mods_disabled.txt</code>. Remove that line to enable it again, then restart.</p><p>Wood also accepts raw <code>.lua</code> files for development and older releases.</p><h2>Menu controls</h2><p><kbd>F10</kbd> opens or closes Wood. Select a mod for Settings or Info. Search and the All, Active, and Settings filters help find mods. <kbd>Escape</kbd> returns to the list, then closes the menu. On speedrun completion and death result screens, Wood scrolls the successfully loaded mod list like credits and holds at the final entry.</p><h2 id="time-warp">Time Warp</h2><p>A separate practice mod. Choose 0.05×–4× speed in its settings. F6 halves speed, F7 resets to 1×, and F8 doubles it. Use Enter or Apply for an exact speed. Check your category’s rules before submitting a run.</p><h2 id="wood-utilities">Wood Utilities</h2><p>A separate mod for auto-speedrunner mode, soundtrack preference, application volume, and mouse sensitivity. Open its F10 settings; preferences save automatically.</p><h2 id="uninstall">Uninstall Wood</h2><p>Close TUNG. Use Windows Settings → Apps → Wood for TUNG → Uninstall, or run <code>WoodUninstall.exe</code> in the game folder. Personal settings and custom mods remain. Setup-owned runtime files are removed and replaced originals are restored. Top-level individual mods, settings, and unrelated loader files remain.</p><h2 id="troubleshooting">Troubleshooting</h2><details><summary>TUNG was not detected</summary><p>Browse to the Steam game folder containing <code>TUNG.exe</code> and <code>TUNG/Binaries/Win64</code>.</p></details><details><summary>F10 does not open Wood</summary><p>Wait for the game to initialize. Read <code>TUNG/Binaries/Win64/ue4ss/UE4SS.log</code>. If runtime files are missing, close TUNG and run setup again.</p></details><details><summary>A mod is missing or has an error</summary><p>Check the top-level Mods folder, file extension, and disabled list. Filenames starting with an underscore are skipped. Restart after changes. Read the mod’s Info/Settings page and the UE4SS log.</p></details><details><summary>I already use another loader</summary><p>Setup stops if it finds an incompatible <code>dwmapi.dll</code> proxy. Do not overwrite it manually.</p></details>'''

ABOUT = '''<h2>Wood is the loader</h2><p>Wood loads TUNG mods and hosts their menus and settings. Time Warp, Wood Utilities, and Coordinates are separate mods with their own releases.</p><h2>How it works</h2><p>UE4SS starts Wood inside TUNG. Wood scans the game’s top-level Mods folder for Lua files and .tungmod packages, then builds the F10 menu with Unreal widgets. Mod preferences live in .wood, separately from game saves.</p><h2>License</h2><p>Wood source is MIT licensed. UE4SS retains its upstream license, included with the runtime. Wood is independent of TUNG and its developers.</p>'''

LIVE_SPLIT = '''<div class="actions"><a class="btn" href="downloads/WoodLiveSplit.zip" download>Download Wood LiveSplit setup</a><a class="btn secondary" href="downloads/WoodLiveSplit.tungmod" download>Mod only</a><a class="textlink" href="https://livesplit.org/downloads/">Get LiveSplit</a></div><p>The setup includes the mod, component, layout, eight splits and double-click installer.</p><h2 id="setup">Install once</h2><ol><li><a href="downloads.html">Install Wood</a> first. Install LiveSplit 1.8.37, then close TUNG and LiveSplit.</li><li>Download the setup ZIP and extract <strong>all</strong> files.</li><li>Run <code>Install-WoodLiveSplit.bat</code>. It finds TUNG through Steam and asks for <code>LiveSplit.exe</code> if needed.</li><li>Use the new <strong>TUNG LiveSplit</strong> desktop shortcut to open the supplied layout and splits.</li><li>Launch TUNG through Steam and start a fresh <strong>normal Speedrun</strong> attempt.</li></ol><div class="callout">Updates preserve the saved splits and PBs in the installed WoodTUNG folder. The mod-only download updates an existing setup: close TUNG and replace its package in the top-level Mods folder.</div><h2 id="route">Automatic splits</h2><table><thead><tr><th>Split</th><th>Trigger</th></tr></thead><tbody><tr><td>Valves unlocked</td><td>The valve objective becomes available.</td></tr><tr><td>Valve 1-4</td><td>Each distinct valve interaction, in any order. Repeated clicks count once.</td></tr><tr><td>Door</td><td>The factory door opens.</td></tr><tr><td>Hedge</td><td>Player Z reaches 360-425 after the door opens. Horizontal position and landing are ignored.</td></tr><tr><td>Finish</td><td>The game displays its final result. LiveSplit uses that result time.</td></tr></tbody></table><h2 id="testing">Test your setup</h2><ol><li>Open the shortcut before starting an attempt. LiveSplit should start with the game clock.</li><li>Click a valve: the split fires without waiting for its animation.</li><li>Complete the route and compare the final time with the game result.</li><li>Retry: a fresh attempt resets the run started by this mod. Manual reset waits for the next fresh attempt; manual pause is respected.</li></ol><p>Tiny Tung, B-hop and checkpoint modes are excluded. Attaching mid-attempt waits for a fresh start. A one-segment run named <code>Finish</code> is also supported.</p><h2 id="manual">Manual installation</h2><ol><li>Copy <code>WoodLiveSplit.tungmod</code> into TUNG's top-level <code>Mods</code> folder.</li><li>With LiveSplit closed, copy <code>LiveSplit.WoodTUNG.dll</code> into its <code>Components</code> folder.</li><li>Reopen LiveSplit. Use <strong>Open Splits / From File</strong> for <code>TUNG-AnyPercent.lss</code> and <strong>Open Layout / From File</strong> for <code>Wood-TUNG.lsl</code>.</li></ol><h2 id="help">Troubleshooting</h2><details><summary>Setup cannot find the game or timer</summary><p>Select TUNG.exe or LiveSplit.exe when prompted. Wood must already be installed.</p></details><details><summary>The timer does not start</summary><p>Load the Wood layout, enable the mod, and start a fresh normal Speedrun attempt. Check status on the Wood mod settings page or the component's layout settings.</p></details><details><summary>I already have saved splits</summary><p>Keep your file and load it instead of the supplied blank run if it uses the same eight segment names, or one Finish segment. Switching to a layout without the Wood component stops automation.</p></details>'''
