# RenderBatch v1.2.0

Third release of RenderBatch, a modern batch rendering tool for Blender files.

## New Features
- **Settings Management**: Added settings button to configure custom Blender executable path
- **Persistent Settings**: Blender path is automatically saved between sessions
- **Path Validation**: Automatic validation of Blender executable before rendering
- **Enhanced User Experience**: Clear feedback for settings operations

## Previous Features
- Batch rendering of Blender files
- Modern dark theme UI with drag and drop interface
- Auto-retry functionality for failed renders
- Progress tracking and status updates
- Job queue management with reordering capabilities
- Persistent job list between sessions
- Version information display
- Improved error handling and reporting
- Enhanced UI responsiveness
- Better file path handling for non-ASCII characters

## Requirements
- Windows 10 or later
- Blender 4.3 or later (can be installed in any location)

## Installation
1. Download the RenderBatch.exe file
2. Run the executable
3. No installation required - it's a portable application

## Usage
1. Launch RenderBatch.exe
2. **First time setup**: Click "⚙️ Settings" to select your Blender executable (blender.exe)
3. Add Blender files by dragging and dropping or using the "Add Files" button
4. Configure auto-retry if desired
5. Click "Start Batch Render" to begin processing
6. Monitor progress in the job list
7. Cancel rendering at any time using the "Cancel Render" button

## Settings
- **Blender Path**: Click the "⚙️ Settings" button to select your Blender executable
- The path is automatically saved and will be used for all future renders
- If no custom path is set, the default location is used: `C:\Program Files\Blender Foundation\Blender 4.4\blender.exe`

## Notes
- The application stores job information and settings in AppData/BlueMoonVirtual/RenderBatch
- Settings are automatically saved between sessions
- For non-ASCII characters in file paths, ensure your system locale supports them 