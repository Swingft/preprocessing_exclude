#!/bin/bash

# Tilde(~) expansion can be tricky inside quoted strings in scripts.
# Using the $HOME variable is a safer and more reliable way to refer to the user's home directory.
BASE_SDK_PATH="/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk/System/Library/Frameworks"
DEST_DIR="$HOME/PycharmProjects/preprocessing_exclude/apple_sdk_headers"

# Create the destination directory if it doesn't exist.
# The -p flag ensures it doesn't error if the directory already exists.
echo "Ensuring destination directory exists: $DEST_DIR"
mkdir -p "$DEST_DIR"

# Get all .framework directories and extract just the framework names
echo "Scanning for all frameworks..."
framework_count=0

for fw_path in "$BASE_SDK_PATH"/*.framework; do
  # Extract just the framework name without path and .framework extension
  fw=$(basename "$fw_path" .framework)

  # Skip if framework directory doesn't exist (shouldn't happen, but safety check)
  if [ ! -d "$fw_path" ]; then
    continue
  fi

  echo "Copying headers from $fw.framework..."

  # Count how many .h files we're copying from this framework
  header_count=$(find "$fw_path" -name "*.h" 2>/dev/null | wc -l)

  if [ "$header_count" -gt 0 ]; then
    find "$fw_path" -name "*.h" -exec cp -p {} "$DEST_DIR"/ \; 2>/dev/null
    echo "  → Copied $header_count header files"
  else
    echo "  → No header files found"
  fi

  framework_count=$((framework_count + 1))
done

echo "Processed $framework_count frameworks total."

echo "Header copy complete."