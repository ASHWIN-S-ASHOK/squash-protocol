#!/bin/bash
set -e

REPO_DIR="squash-core/build/repo"

if [ -z "$MAVEN_USERNAME" ] || [ -z "$MAVEN_PASSWORD" ]; then
    echo "Error: MAVEN_USERNAME or MAVEN_PASSWORD environment variables are not set."
    exit 1
fi

GROUP_PATH="io/github/ashwin-s-ashok"
COMPONENTS_DIR="$REPO_DIR/$GROUP_PATH"

if [ ! -d "$COMPONENTS_DIR" ]; then
    echo "Error: Directory $COMPONENTS_DIR does not exist."
    exit 1
fi

echo "Scanning $COMPONENTS_DIR for Kotlin Multiplatform components..."

# Iterate over each component (squash-core, squash-core-jvm, etc)
for component in "$COMPONENTS_DIR"/*; do
    if [ -d "$component" ]; then
        component_name=$(basename "$component")
        echo "============================================================"
        echo "Processing component: $component_name"
        
        # Sonatype Central Portal API requires a ZIP file containing the files for a SINGLE component.
        # It deduces the group and artifact id from the POM inside the zip.
        TMP_DIR=$(mktemp -d)
        mkdir -p "$TMP_DIR/$GROUP_PATH"
        cp -r "$component" "$TMP_DIR/$GROUP_PATH/"
        
        ZIP_FILE="/tmp/${component_name}.zip"
        (cd "$TMP_DIR" && zip -q -r "$ZIP_FILE" .)
        
        echo "Uploading $component_name to Maven Central..."
        
        HTTP_STATUS=$(curl -s -o /tmp/upload_response.txt -w "%{http_code}" -u "$MAVEN_USERNAME:$MAVEN_PASSWORD" \
             -X POST \
             -F "bundle=@$ZIP_FILE" \
             -F "publishingType=AUTOMATIC" \
             "https://central.sonatype.com/api/v1/publisher/upload")
             
        if [ "$HTTP_STATUS" -eq 201 ]; then
            echo "✅ Successfully uploaded $component_name (Upload ID: $(cat /tmp/upload_response.txt))"
        else
            echo "❌ Failed to upload $component_name. Status: $HTTP_STATUS"
            cat /tmp/upload_response.txt
            exit 1
        fi
        
        rm -rf "$TMP_DIR" "$ZIP_FILE"
    fi
done

echo "============================================================"
echo "All components successfully uploaded to Maven Central!"
