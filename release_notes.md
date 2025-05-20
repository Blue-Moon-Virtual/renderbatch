# RenderBatch v1.1.0

Second release of RenderBatch, a modern batch rendering tool for Blender files.

## New Features
- Added version information display
- Improved error handling and reporting
- Enhanced UI responsiveness
- Better file path handling for non-ASCII characters
- Improved drag and drop functionality

## Features
- Batch rendering of Blender files
- Modern dark theme UI with drag and drop interface
- Auto-retry functionality for failed renders
- Progress tracking and status updates
- Job queue management with reordering capabilities
- Persistent job list between sessions

## Requirements
- Windows 10 or later
- Blender 4.3 or later installed at the default location

## Installation
1. Download the RenderBatch.exe file
2. Run the executable
3. No installation required - it's a portable application

## Usage
1. Launch RenderBatch.exe
2. Add Blender files by dragging and dropping or using the "Add Files" button
3. Configure auto-retry if desired
4. Click "Start Batch Render" to begin processing
5. Monitor progress in the job list
6. Cancel rendering at any time using the "Cancel Render" button

## Notes
- The application stores job information in AppData/BlueMoonVirtual/RenderBatch
- Make sure Blender is installed at the default location (C:\Program Files\Blender Foundation\Blender 4.3\blender.exe)
- For non-ASCII characters in file paths, ensure your system locale supports them 