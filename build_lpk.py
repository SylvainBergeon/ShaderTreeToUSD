'''
This helps generate the index.xml file you need to unpack a kit using the .lpk installers.
Fill in the Setup Variables below, and the index.xml file will show up in your kit directory.
It also packages all files into a .lpk file (which is a zip archive with a different extension).
'''

import os
import zipfile
import shutil

#Setup Variables for Kit
kitFolder = '/Users/sylvainbergeon/Library/Application Support/Luxology/Kits/ShaderTreeToUSD'
kitName = 'ShaderTreeToUSD'
kitMessage = '%s Kit installation complete.' % kitName
modoVersion = "801"
installAlias = 'kit'

platformSpecifiPath = {
    "libs-mac":"MacOSX",
    "libs-win":"Win64",
    "libs-linux":"linux"
}

ignorepath = [".git", ".qodo", ".vscode"]
ignorefiles = [".DS_Store", ".gitignore", "build_lpk.py"]

def listFiles(kitPath):
    '''
    Takes a directory to your kit and scans for files to be unpacked by the lpk file
    '''
    files = []
    for r, d, f in os.walk(kitFolder):
        
        # Check if the current directory should be ignored
        should_ignore_dir = False
        for path in ignorepath:
            if path in r:
                print(f"Ignoring directory: {r} (contains {path})")
                should_ignore_dir = True
                break
                
        if should_ignore_dir:
            continue
                
        for n in f:
            # Check if the current file should be ignored
            should_ignore_file = False
            for file in ignorefiles:
                if file == n:
                    print(f"Ignoring file: {n}")
                    should_ignore_file = True
                    break
                    
            if not should_ignore_file:
                file_path = os.path.join(r,n).replace(kitFolder, '').replace('\\','/')
                print(f"Adding file: {file_path}")
                files.append(file_path)
    return files
    
def buildIndexText(kitName, targetDir, files, kitMessage, modoVersion):
    '''
    Creates a string to be written to the index.xml
    '''
    tmp = '<?xml version="1.0" encoding="utf-8"?>\n<package version="%s">' % modoVersion #Headers
    tmp += ('\n\t<%s name="%s" restart="YES">' % (targetDir, kitName)) #Kit Name and Restart option
    for i in files:
        platform = ""
        for subpath in platformSpecifiPath:
            if subpath in i:
                platform = f' platform="{platformSpecifiPath[subpath]}"'
                break  # Exit once we've found a match
        tmp += ('\n\t\t<source target="%s%s" %s>%s</source>' % (kitName, i, platform, i[1:]))  #Append each file to unpack
    tmp += ('\n\t</%s>\n\t<message button="Help">%s</message>\n</package>' % (targetDir, kitMessage))
    return tmp

def create_lpk_archive(kitFolder, kitName, files):
    '''
    Creates a .lpk file (zip archive) containing all the files
    '''
    # Define the output LPK file path
    lpk_path = os.path.join(os.path.dirname(kitFolder), f"{kitName}.lpk")  # Changed .zip to .lpk
    
    print(f"Creating LPK archive: {lpk_path}")
    
    # Create a new zip file
    with zipfile.ZipFile(lpk_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add index.xml to the root of the archive
        index_path = os.path.join(kitFolder, 'index.xml')
        zipf.write(index_path, 'index.xml')
        
        # Add all other files
        for file_path in files:
            # Get the full path to the file
            full_path = os.path.join(kitFolder, file_path.lstrip('/'))
            
            # Add the file to the archive, preserving the relative path
            zipf.write(full_path, file_path.lstrip('/'))
    
    print(f"LPK archive created successfully: {lpk_path}")
    return lpk_path
    
#/////////////////////////////////////// Main execution
# Build list of files to incorporate
files = listFiles(kitFolder)

# Generate and save index.xml
index = buildIndexText(kitName, installAlias, files, kitMessage, modoVersion)
index_path = os.path.join(kitFolder, 'index.xml')
with open(index_path, 'w+') as f:
    f.write(index)
print(f"Created index.xml at {index_path}")

# Create the LPK archive
lpk_file = create_lpk_archive(kitFolder, kitName, files)
print(f"LPK file created at: {lpk_file}")