# MuseWave Deployment Fix - Build Command Issue

## Problem Identified

**Error:**
```
sh: line 1: craco: command not found
Error: Command "cd frontend && npm run build" exited with 127
```

**Root Cause:**
- `craco` CLI was not available in the build environment
- `@craco/craco` package exists in devDependencies but wasn't being called correctly
- The build command tried to execute `craco` directly without `npx` prefix
- Dependencies weren't explicitly installed in the build phase

## Solution Applied

### 1. Updated Frontend Build Scripts
**File:** `frontend/package.json`

Changed build scripts to use `npx craco` to ensure the CLI is properly resolved:
```json
"scripts": {
  "start": "npx craco start",
  "build": "npx craco build",
  "test": "npx craco test"
}
```

**Why:** `npx` automatically finds and executes the `craco` command from node_modules, even if it's not globally installed.

### 2. Updated Vercel Build Configuration
**File:** `vercel.json`

Added explicit install command and ensure npm install runs before build:
```json
{
  "version": 2,
  "buildCommand": "cd frontend && npm install && npm run build",
  "outputDirectory": "frontend/build",
  "framework": "create-react-app",
  "installCommand": "cd frontend && npm install",
  "rewrites": [
    {
      "source": "/api/:path*",
      "destination": "https://your-backend-api-url/api/:path*"
    },
    {
      "source": "/((?!api).*)",
      "destination": "/index.html"
    }
  ]
}
```

**Why:** 
- Explicitly installs dependencies before building
- Ensures `@craco/craco` is available when `npm run build` executes
- Guarantees proper dependency resolution

## Build Process Flow

```
1. Vercel detects changes
   ↓
2. Installs backend dependencies (if any)
   ↓
3. Runs installCommand: "cd frontend && npm install"
   ↓
4. Installs all devDependencies including @craco/craco
   ↓
5. Runs buildCommand: "cd frontend && npm install && npm run build"
   ↓
6. npm run build executes "npx craco build"
   ↓
7. npx resolves craco from node_modules
   ↓
8. craco uses craco.config.js to configure React build
   ↓
9. React app built and output to frontend/build
   ↓
10. Vercel deploys build artifacts
```

## Files Modified

- ✅ `frontend/package.json` - Updated scripts to use npx
- ✅ `vercel.json` - Added installCommand and explicit npm install in buildCommand

## Verification Steps

To test locally before deployment:

```bash
# From project root
cd frontend
npm install
npm run build

# Should complete without "craco: command not found" error
```

## Expected Build Output

After fix, build should show:
```
15:21:13.713 > frontend@0.1.0 build
15:21:13.713 > npx craco build
```

Instead of:
```
15:21:13.713 > frontend@0.1.0 build
15:21:13.713 > craco build
15:21:13.719 sh: line 1: craco: command not found
```

## Next Steps

1. Push changes to main branch
2. Vercel will automatically trigger a new deployment
3. Monitor build logs for successful completion
4. Verify application loads at https://muse-wave-emergent-ai.vercel.app

## Additional Notes

- `@craco/craco` is the correct package name (version 7.1.0)
- `craco` is the CLI command provided by `@craco/craco`
- Using `npx` ensures cross-platform compatibility (works on Windows, Mac, Linux)
- No changes needed to `craco.config.js` - it's correctly configured

## Related Files

- `craco.config.js` - CRA configuration overrides (no changes needed)
- `vercel.json` - Build/deployment configuration (updated)
- `package.json` - npm scripts (updated to use npx)

---

**Status:** ✅ Ready for deployment
**Date Updated:** February 15, 2026
