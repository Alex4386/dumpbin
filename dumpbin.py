from pathlib import Path
import urllib.request
import json
import re
import shutil
import zipfile
import sys
import os

DOWNLOADS = Path("Downloads")
RELEASES = Path("Releases")

# Ensure directories exist
DOWNLOADS.mkdir(exist_ok=True)
RELEASES.mkdir(exist_ok=True)

def download(url):
	with urllib.request.urlopen(url) as resp:
		return resp.read()

def get_sub_dirs(path):
	return [x for x in path.iterdir() if x.is_dir()]

MANIFEST_URL = "https://aka.ms/vs/17/release/channel"
print("Checking Visual Studio Manifest...")
chman = json.loads(download(MANIFEST_URL))
vsman_url = chman["channelItems"][0]["payloads"][0]["url"]
license = chman["channelItems"][1]["localizedResources"][0]["license"]
vsman = json.loads(download(vsman_url))
packages = vsman["packages"]

version = ""
filename = ""
url = ""
for i in range(len(packages)-1, -1, -1):
	if re.fullmatch(r"Microsoft.VC.[\d.]+.Tools.HostX64.TargetX64.base", packages[i]["id"]):
		version = packages[i]["version"]
		filename = packages[i]["payloads"][0]["fileName"]
		url = packages[i]["payloads"][0]["url"]
		break

# Check for auto-accept via environment variable or command line argument
auto_accept = (
	os.getenv("ACCEPT_VS_LICENSE", "").upper() in ["1", "YES", "Y", "TRUE"] or
	"--accept-license" in sys.argv or
	not sys.stdin.isatty()  # Non-interactive environment (like CI)
)

if auto_accept:
	print(f"Automatically accepting Microsoft Visual Studio license: {license}")
	yes = "Y"
else:
	yes = input(f"Do you accept Microsoft Visual Studio license: {license} [Y/N] ? ")

if yes.upper() not in ["", "YES", "Y"]:
	exit(0)

print(f"Downloading {filename}...")
with open(DOWNLOADS / filename, "wb") as file:
	file.write(download(url))

print(f"Unpacking {filename}...")
ARCHIVES = DOWNLOADS / "Archives"
shutil.rmtree(ARCHIVES, ignore_errors=True)
shutil.unpack_archive(DOWNLOADS / filename, ARCHIVES, "zip")

print(f"Creating Zip in {RELEASES.resolve()}...")
BIN = get_sub_dirs(ARCHIVES / "Contents/VC/Tools/MSVC")[0] / "bin/Hostx64/x64"
files = ["dumpbin.exe", "link.exe", "link.exe.config", "tbbmalloc.dll", "mspdbcore.dll"]
with zipfile.ZipFile(RELEASES / f"dumpbin-{version}-x64.zip", "w", zipfile.ZIP_LZMA) as z:
	for f in files:
		path = BIN / f
		if path.exists():
			z.write(path, path.name)
		else:
			print(f"Warning: {f} not found at {path}")

print("Done!")
