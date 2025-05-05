bl_info = {
    "name": "CGI Virtual Tour Render Helper",
    "blender": (3, 0, 0),
    "category": "Render",
    "author": "Your Name",
    "version": (2, 9),
    "description": "Dynamically adjusts render resolution based on frame number for CGI Virtual Tour",
    "location": "Render > CGI Virtual Tour",
}

import bpy
import os
import sys
from bpy.app.handlers import persistent
from bpy.props import BoolProperty, IntProperty, StringProperty

def update_virtual_tour(self, context):
    if context.scene:
        apply_render_settings(context.scene)

def register_scene_properties():
    bpy.types.Scene.cgi_virtual_tour_enabled = BoolProperty(
        name="Enable CGI Virtual Tour",
        default=False,
        description="Enable the CGI Virtual Tour render helper",
        update=update_virtual_tour,
    )
    bpy.types.Scene.panoramic_count = IntProperty(
        name="Panoramic Images",
        default=0,
        min=0,
        description="Number of panoramic images (8000x4000)",
        update=update_virtual_tour,
    )
    bpy.types.Scene.output_directory = StringProperty(
        name="Output Directory",
        description="Directory where rendered images will be saved",
        default="//",
        subtype='DIR_PATH',
    )
    bpy.types.Scene.filename_pattern = StringProperty(
        name="Filename Pattern",
        description="Pattern for naming rendered files (use {frame:04d} for frame number)",
        default="frame_{frame:04d}",
    )

def unregister_scene_properties():
    del bpy.types.Scene.cgi_virtual_tour_enabled
    del bpy.types.Scene.panoramic_count
    del bpy.types.Scene.output_directory
    del bpy.types.Scene.filename_pattern

def apply_render_settings(scene):
    if scene is None or not scene.cgi_virtual_tour_enabled:
        return

    current_frame = scene.frame_current
    panoramic_count = scene.panoramic_count

    if 1 <= current_frame <= panoramic_count:
        scene.render.resolution_x = 8000
        scene.render.resolution_y = 4000
        scene.cycles.samples = 250
    else:
        scene.render.resolution_x = 1920
        scene.render.resolution_y = 1120
        scene.cycles.samples = 1000

@persistent
def frame_update_handler(scene, depsgraph=None):
    if scene is not None:
        apply_render_settings(scene)

@persistent
def render_pre_handler(scene):
    if scene is not None:
        apply_render_settings(scene)

@persistent
def load_handler(dummy):
    print("CGI Virtual Tour Add-on: Re-registering handlers")
    if frame_update_handler not in bpy.app.handlers.frame_change_pre:
        bpy.app.handlers.frame_change_pre.append(frame_update_handler)
    if render_pre_handler not in bpy.app.handlers.render_pre:
        bpy.app.handlers.render_pre.append(render_pre_handler)
    scene = getattr(bpy.context, "scene", None)
    if scene is not None:
        apply_render_settings(scene)

@persistent
def call_virtual_tour_operator(dummy):
    try:
        bpy.ops.render.virtual_tour_animation()
    except Exception as e:
        print("Error calling virtual tour operator:", e)

class RENDER_OT_virtual_tour_animation(bpy.types.Operator):
    
    bl_idname = "render.virtual_tour_animation"
    bl_label = "Render Virtual Tour Animation"
    bl_description = (
        "Render an animation with dynamic resolution changes.\n"
        "Each frame is rendered with its unique settings and output file."
    )
    
    def execute(self, context):
        import os
        scene = context.scene
        original_frame = scene.frame_current

        output_dir = bpy.path.abspath(scene.output_directory)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        try:
            for frame in range(scene.frame_start, scene.frame_end + 1):
                scene.frame_set(frame)
                apply_render_settings(scene)
                
                file_name = scene.filename_pattern.format(frame=frame)
                fmt = scene.render.image_settings.file_format
                ext = ".jpg" if fmt == 'JPEG' else ".png" if fmt == 'PNG' else ""
                new_filepath = os.path.join(output_dir, file_name + ext)
                scene.render.filepath = new_filepath
                
                print(f"Rendering frame {frame}: {scene.render.resolution_x}x{scene.render.resolution_y} -> {new_filepath}")
                try:
                    bpy.ops.render.render(write_still=True)
                except Exception as e:
                    error_msg = str(e)
                    if "out of memory" in error_msg.lower() or "cuda" in error_msg.lower():
                        print(f"GPU Memory Error on frame {frame}: {error_msg}")
                        if bpy.app.background:
                            print("Exiting Blender due to GPU memory error")
                            os._exit(1)
                        return {'CANCELLED'}
                    else:
                        print(f"Error rendering frame {frame}: {error_msg}")
                        if bpy.app.background:
                            print("Exiting Blender due to render error")
                            os._exit(1)
                        return {'CANCELLED'}
            
            scene.frame_set(original_frame)
            scene.render.filepath = output_dir

            if bpy.app.background:
                print("Custom render complete. Exiting Blender immediately.")
                os._exit(0)

            return {'FINISHED'}
        except Exception as e:
            print(f"Unexpected error during rendering: {str(e)}")
            if bpy.app.background:
                print("Exiting Blender due to unexpected error")
                os._exit(1)
            return {'CANCELLED'}

class RENDER_PT_virtual_tour_panel(bpy.types.Panel):
    bl_label = "CGI Virtual Tour"
    bl_idname = "RENDER_PT_virtual_tour_panel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "render"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        if scene:
            layout.prop(scene, "cgi_virtual_tour_enabled")
            layout.prop(scene, "panoramic_count", slider=True)
            if scene.cgi_virtual_tour_enabled:
                layout.prop(scene, "output_directory")
                layout.prop(scene, "filename_pattern")
                layout.separator()
                layout.label(text="For animation renders, use:")
                layout.operator("render.virtual_tour_animation", icon="RENDER_ANIMATION")
        else:
            layout.label(text="No active scene found")

def register():
    register_scene_properties()
    bpy.utils.register_class(RENDER_OT_virtual_tour_animation)
    bpy.utils.register_class(RENDER_PT_virtual_tour_panel)

    if load_handler not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(load_handler)
    load_handler(None)

    if "-a" in sys.argv:
        bpy.app.handlers.load_post.append(call_virtual_tour_operator)
        sys.argv.remove("-a")

def unregister():
    bpy.utils.unregister_class(RENDER_PT_virtual_tour_panel)
    bpy.utils.unregister_class(RENDER_OT_virtual_tour_animation)
    unregister_scene_properties()

    if frame_update_handler in bpy.app.handlers.frame_change_pre:
        bpy.app.handlers.frame_change_pre.remove(frame_update_handler)
    if render_pre_handler in bpy.app.handlers.render_pre:
        bpy.app.handlers.render_pre.remove(render_pre_handler)
    if load_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(load_handler)
    if call_virtual_tour_operator in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(call_virtual_tour_operator)

if __name__ == "__main__":
    register()