# Host Wood on Netlify

The website is plain HTML, CSS, and JavaScript. It needs no ChatGPT account,
Sites service, backend, environment variables, or paid Netlify feature.

## First upload

1. Extract `release/Wood-Netlify.zip` into a folder named `Wood-Netlify`.
2. Open https://app.netlify.com/drop and sign in to your Netlify account.
3. Drag the **Wood-Netlify folder** onto the upload area. Its top level must
   contain `index.html`, `style.css`, `site.js`, `_headers`, and `downloads/`.
   Upload the entire folder, including the installer in `downloads/`.
4. Netlify gives you a public `https://<site-name>.netlify.app` address. In the
   project's settings, change the project name to `woodlauncher` if available;
   otherwise choose another available name. No custom domain purchase is needed.
5. Open the published Downloads page and download `WoodSetup.exe`. Compare its
   SHA-256 with the value on the page and `downloads/SHA256SUMS.txt`.

You can add a domain you own later under Netlify's domain management settings.
The existing ChatGPT-hosted site is separate; this package contains no dependency
on it and publishing the package does not delete or redirect that old site.

## Updates

Upload a freshly extracted package to the **same project's Deploys page**.
Using Netlify Drop again creates another project, so use the existing project
for subsequent releases. Upload the whole folder to update the download and its
checksum together. Manual uploads require no build command or publish-directory
setting in the dashboard.

## Rebuild the upload package

On Windows, from the WoodTools source folder:

```powershell
.venv/Scripts/python scripts/build_release.py
.venv/Scripts/python scripts/package_netlify.py
```

The second command rebuilds and verifies the website and produces
`release/Wood-Netlify.zip`. Do not upload the source repository, game files,
`payload/`, `.wood/`, or `.build/`.

`netlify.toml` supports a local CLI deployment of the prebuilt `site/dist` folder.
Git-based continuous deployment is not configured: release executables are
intentionally excluded from Git, and the Windows installer cannot be built on
Netlify's Linux build workers. Use this manual package until a public release
download source and a suitable publishing workflow are configured.

Official instructions: https://docs.netlify.com/manage/projects/add-new-project/
