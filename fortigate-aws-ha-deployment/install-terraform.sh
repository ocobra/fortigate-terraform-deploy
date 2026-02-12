#!/bin/bash
# Install Terraform on Linux

set -e

echo "🔧 Installing Terraform..."
echo "================================"

# Detect architecture
ARCH=$(uname -m)
if [ "$ARCH" = "x86_64" ]; then
    TERRAFORM_ARCH="amd64"
elif [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
    TERRAFORM_ARCH="arm64"
else
    echo "❌ Unsupported architecture: $ARCH"
    exit 1
fi

# Set Terraform version
TERRAFORM_VERSION="1.7.5"

echo "📦 Downloading Terraform ${TERRAFORM_VERSION} for Linux ${TERRAFORM_ARCH}..."

# Download Terraform
cd /tmp
wget -q "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_${TERRAFORM_ARCH}.zip"

# Unzip
echo "📂 Extracting Terraform..."
unzip -q -o "terraform_${TERRAFORM_VERSION}_linux_${TERRAFORM_ARCH}.zip"

# Install to user's local bin (no sudo required)
mkdir -p ~/.local/bin
mv terraform ~/.local/bin/

# Clean up
rm "terraform_${TERRAFORM_VERSION}_linux_${TERRAFORM_ARCH}.zip"

echo ""
echo "✅ Terraform installed successfully!"
echo ""
echo "📍 Terraform location: ~/.local/bin/terraform"
echo ""

# Check if ~/.local/bin is in PATH
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo "⚠️  ~/.local/bin is not in your PATH"
    echo ""
    echo "Add this line to your ~/.bashrc or ~/.zshrc:"
    echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo ""
    echo "Then run:"
    echo "    source ~/.bashrc  # or source ~/.zshrc"
    echo ""
    echo "Or run Terraform directly:"
    echo "    ~/.local/bin/terraform version"
else
    echo "✅ ~/.local/bin is already in your PATH"
    terraform version
fi

echo ""
echo "🎉 Installation complete!"
