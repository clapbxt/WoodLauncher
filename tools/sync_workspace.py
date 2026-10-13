"""Mirror only publishable application source into the runtime Git checkout."""
from pathlib import Path
import argparse
import os
import shutil

REPOSITORY = Path(__file__).resolve().parents[1]
SKIP = {'.git', '.build', '.venv', 'node_modules', '__pycache__', 'release',
        'payload', 'dist', 'test-results', 'runtime-source', '.netlify'}
EXTENSIONS = {'.py', '.lua', '.md', '.txt', '.bat', '.ps1', '.json', '.toml',
              '.js', '.mjs', '.css', '.png', '.svg', '.cs', '.lsl', '.lss'}


def sync(workspace):
    workspace = Path(workspace).resolve()
    for name in ('WoodLauncher', 'WoodSetup', 'WoodWebsite', 'WoodModPackager', 'WoodLiveSplit', 'BuildEnvironment'):
        source = workspace / name
        for folder, directories, filenames in os.walk(source):
            directories[:] = [item for item in directories if item not in SKIP]
            for filename in filenames:
                path = Path(folder) / filename
                relative = path.relative_to(source)
                if path.suffix.lower() not in EXTENSIONS and path.name not in {'LICENSE', '.gitignore'}:
                    continue
                target = REPOSITORY / name / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)
                if target.suffix.lower() in {'.py', '.lua', '.json', '.md'}:
                    target.write_text(target.read_text(encoding='utf-8').rstrip('\r\n') + '\n',
                                      encoding='utf-8', newline='\n')
    target = REPOSITORY / 'WoodWebsite/release/versions.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(workspace / 'WoodWebsite/release/versions.json', target)
    (target.parent / 'downloads').mkdir(exist_ok=True)
    shutil.copy2(workspace / 'DEVELOPMENT.md', REPOSITORY / 'DEVELOPMENT.md')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('workspace', type=Path)
    sync(parser.parse_args().workspace)
