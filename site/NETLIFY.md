# Deploy Wood on Netlify

The site uses Netlify Functions and persistent Netlify Blobs storage for the
official mod collection. A static Netlify Drop upload is not sufficient: it
would publish the pages but disable the catalog API and curator uploads.

## Build the deployment bundle

From the WoodTools source folder on Windows:

```powershell
.\.venv\Scripts\python.exe scripts\build_release.py
.\.venv\Scripts\python.exe scripts\verify_distribution.py
.\.venv\Scripts\python.exe scripts\package_netlify.py
```

This builds `WoodSetup.exe`, `WoodLauncher.exe`, and `WoodModPackager.exe`,
generates the site, runs the site checks, and creates `release/Wood-Netlify.zip`. The ZIP contains the
published static site, Netlify Function source, Netlify configuration, and npm
manifests. It does not contain `node_modules`, credentials, game files, or source
build caches. It is a **Netlify CLI deployment bundle**, not a Drag & Drop ZIP.

## First deployment

1. Extract `release/Wood-Netlify.zip` into a permanent folder and open a
   terminal in the extracted folder.
2. Install the pinned function dependency with `npm ci`.
3. Run `npx netlify-cli login`, then `npx netlify-cli link` and follow the prompts
   to create or select the Netlify site.
4. Generate a private token locally in PowerShell:

   ```powershell
   $bytes = New-Object byte[] 32
   $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
   $rng.GetBytes($bytes)
   $token = [Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+','-').Replace('/','_')
   Set-Clipboard -Value $token
   $rng.Dispose()
   ```

   This creates a random 256-bit token and copies it to the clipboard. Netlify
   does not issue this token for you; you create it. Keep it private.
5. In that site's Netlify dashboard, open **Site configuration → Environment
   variables** and add `MOD_ADMIN_TOKEN`. Paste the generated token as its value
   and make it available to Functions. Do not put the value in site files,
   source control, or the deployment ZIP.
6. Configure Netlify Blobs access for the deployed function. In **Site
   configuration → General → Site details**, copy the site's Site ID and add it
   as the `NETLIFY_SITE_ID` environment variable. Create a Netlify personal
   access token in your Netlify user settings and add it as `NETLIFY_AUTH_TOKEN`.
   Make both variables available to Functions.
   Keep this account credential private and server-side; do not use it as the
   curator token or put it in the website. Netlify Functions normally receive
   Blobs credentials automatically, but these explicit variables allow the
   catalog to work with CLI deployments that lack that runtime context.
7. Deploy from the extracted project folder:

   ```powershell
   npx netlify-cli deploy --prod --dir site/dist
   ```

   The CLI reads `netlify.toml`, publishes `site/dist`, and deploys
   `site/functions/mod-catalog.mjs`. Netlify Blobs persists published Lua files
   and catalog metadata across deploys; it does not need a separate database.
8. Open `/admin.html`, paste that same token into the private curator token field,
   and publish when ready. The token is sent only in the request's Authorization
   header and is not saved in browser storage. A fresh catalog displays no mods
   until one is published. There is no public delete endpoint, so do not publish
   a test entry to the production catalog.

Keep `/admin.html` bookmarked if useful, but treat the token like a password.
Anyone who obtains it can publish official catalog entries. Rotate the value in
Netlify if it is exposed. Public visitors can browse and download; POST uploads
require the configured token.

## Updates

Rebuild the release and deployment ZIP using the commands above. Extract the
updated ZIP over a fresh folder, run `npm ci`, and deploy from the already linked
project with the same CLI command. Keep `MOD_ADMIN_TOKEN`, `NETLIFY_SITE_ID`,
and `NETLIFY_AUTH_TOKEN` configured in Netlify; never copy them into the
extracted project.

The static pages and downloadable executables are included in `site/dist`.
Deploy that folder together with the function using Netlify CLI; uploading only
`site/dist` through Netlify Drop will not run the API or enable uploads.
