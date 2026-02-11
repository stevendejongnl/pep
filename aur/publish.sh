#!/bin/bash
set -euo pipefail

AUR_REPO="/tmp/pep-aur"
PKGNAME="pep"
GITHUB_REPO="stevendejongnl/pep"

# Get latest release tag from GitHub
echo "==> Fetching latest release..."
tag=$(gh release view --repo "$GITHUB_REPO" --json tagName -q .tagName)
version="${tag#v}"
echo "    Found: $tag (version $version)"

# Download tarball and compute sha256
echo "==> Computing sha256..."
sha=$(curl -sL "https://github.com/$GITHUB_REPO/archive/$tag.tar.gz" | sha256sum | cut -d' ' -f1)
echo "    $sha"

# Clone AUR repo if needed
if [ ! -d "$AUR_REPO/.git" ]; then
    echo "==> Cloning AUR repo..."
    rm -rf "$AUR_REPO"
    git clone "ssh://aur@aur.archlinux.org/$PKGNAME.git" "$AUR_REPO"
fi

# Copy files and patch in tmp
echo "==> Updating AUR repo..."
script_dir="$(cd "$(dirname "$0")" && pwd)"
cp "$script_dir/PKGBUILD" "$script_dir/pep.install" "$AUR_REPO/"
sed -i "s/^pkgver=.*/pkgver=$version/" "$AUR_REPO/PKGBUILD"
sed -i "s/^sha256sums=.*/sha256sums=('$sha')/" "$AUR_REPO/PKGBUILD"
cd "$AUR_REPO"
makepkg --printsrcinfo > .SRCINFO

# Commit and push
git add PKGBUILD pep.install .SRCINFO
git commit -m "Update to $version"
git push

echo "==> Published $PKGNAME $version to AUR"
