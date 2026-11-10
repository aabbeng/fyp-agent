# Application

This package contains the safe, deterministic foundation for the local image-management agent.

## Current tools

- `retrieve_images_by_date`: finds supported images by filesystem last-modified date.
- `create_folder`: creates a destination beneath the configured gallery root.
- `copy_images`: copies supported images without overwriting existing files.

Every tool returns a structured `ToolResult`. The controller dispatches only the three explicitly allowlisted tools. Filesystem paths are resolved and rejected when they leave the configured gallery.
