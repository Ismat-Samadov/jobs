import re

# Read the original requirements file
with open('requirements.txt', 'r') as file:
    lines = file.readlines()

# Write back without version specifications
with open('requirements_no_versions.txt', 'w') as file:
    for line in lines:
        # Remove version specifications using regex
        line = re.sub(r'==.*', '', line)
        file.write(line)

# Rename the new file to replace the original if desired
import os
os.replace('requirements_no_versions.txt', 'requirements.txt')
