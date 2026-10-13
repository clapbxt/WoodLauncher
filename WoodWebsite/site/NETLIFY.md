# Deploy Wood on Netlify

The public site serves downloads and the update feed, and uses a Netlify Function plus Netlify Blobs for the mod catalog. Deploy with Netlify CLI so the function is published with the static pages.

## Prepare a release

1. Build the components you are releasing from their own folders: WoodLauncher, WoodSetup, and optionally WoodModPackager.
2. Manually copy selected executables into WoodWebsite/release/downloads/. Copy the LiveSplit ZIP and package too if they are part of this release.
3. Update WoodWebsite/release/versions.json with the launcher and runtime versions.
4. In WoodWebsite, run ..\BuildEnvironment\.venv\Scripts\python.exe scripts/package_website.py.
5. Use WoodWebsite/release/WoodWebsite-Netlify.zip for deployment.

The website builder reads only the manually staged downloads. It calculates their checksums and generates the update feed at site/dist/wood-launcher.json. The launcher checks https://woodlauncher.clapbxt.com/wood-launcher.json at startup. When the launcher or runtime is newer, it asks before updating. Accepting downloads and verifies Setup and launcher, updates the runtime and launcher, then starts TUNG. Declining asks again at the next launch.

## Deploy

Extract the ZIP to a clean folder. In that folder, run:

    npm ci
    npx netlify-cli login
    npx netlify-cli link
    npx netlify-cli deploy --prod --dir site/dist

Link to the existing Netlify project for woodlauncher.clapbxt.com. Keep MOD_ADMIN_TOKEN, NETLIFY_SITE_ID, and NETLIFY_AUTH_TOKEN in the site's server-side environment variables. Do not place secrets in the source tree or ZIP. Netlify Drop does not publish the Function.

For first deployment, generate a private 256-bit curator token in PowerShell and store it in the Netlify site's environment variables as MOD_ADMIN_TOKEN. Copy the site's Site ID into NETLIFY_SITE_ID, and create a Netlify personal access token for NETLIFY_AUTH_TOKEN so the catalog function can use Netlify Blobs. Keep those values server-side and redeploy after configuring them. The curator token is entered only in the private admin page when publishing packages.
