import bpy
from .ui import WATEREDITOR_PT_VIEW_PANEL, WATEREDITOR_PT_OBJECT_PANEL
from .operators import OT_Import_WaterXML, OT_Export_WaterXML
from .overlay import register_overlay, unregister_overlay

bl_info = {
    "name": "WaterEditor",
    "author": "ultrahacx ft Dolu",
    "version": (2, 0),
    "blender": (5, 1, 0),
    "location": "View3D > N",
    "description": "Modify GTAV water.xml",
}


class WaterProperties(bpy.types.PropertyGroup):
    water_type: bpy.props.IntProperty(name="Water Type") # type: ignore
    water_is_invisible: bpy.props.BoolProperty(name="Is Invisible") # type: ignore
    water_has_limited_depth: bpy.props.BoolProperty(name="Has Limited Depth") # type: ignore
    water_limited_depth: bpy.props.FloatProperty(name="Limited Depth") # type: ignore
    water_z: bpy.props.FloatProperty(name="Water Z") # type: ignore
    water_a1: bpy.props.IntProperty(name="A1") # type: ignore
    water_a2: bpy.props.IntProperty(name="A2") # type: ignore
    water_a3: bpy.props.IntProperty(name="A3") # type: ignore
    water_a4: bpy.props.IntProperty(name="A4") # type: ignore
    water_no_stencil: bpy.props.BoolProperty(name="No Stencil") # type: ignore
    water_fDampening: bpy.props.FloatProperty(name="Dampening") # type: ignore
    water_amplitude: bpy.props.FloatProperty(name="Amplitude") # type: ignore
    water_xDirection: bpy.props.FloatProperty(name="xDirection") # type: ignore
    water_yDirection: bpy.props.FloatProperty(name="yDirection") # type: ignore


def register():
    bpy.types.Object.gta_quadtype = bpy.props.EnumProperty(
        name="Quad Type",
        description="Type of water quad",
        items=[
            ('none', "None", "Not a water quad"),
            ('water', "Water Quad", "Water quad"),
            ('calming', "Calming Quad", "Calming quad"),
            ('wave', "Wave Quad", "Wave quad")
        ],
        default='none'
    )

    bpy.utils.register_class(OT_Import_WaterXML)
    bpy.utils.register_class(OT_Export_WaterXML)
    bpy.utils.register_class(WaterProperties)

    bpy.types.Object.waterProperties = bpy.props.PointerProperty(
        type=WaterProperties)

    bpy.utils.register_class(WATEREDITOR_PT_VIEW_PANEL)
    bpy.utils.register_class(WATEREDITOR_PT_OBJECT_PANEL)

    bpy.types.Scene.watereditor_show_wave_overlay = bpy.props.BoolProperty(
        name="Show Wave Directions",
        default=True,
    )

    register_overlay()


def unregister():
    unregister_overlay()
    del bpy.types.Object.gta_quadtype
    del bpy.types.Object.waterProperties
    del bpy.types.Scene.watereditor_show_wave_overlay

    bpy.utils.unregister_class(WATEREDITOR_PT_VIEW_PANEL)
    bpy.utils.unregister_class(WATEREDITOR_PT_OBJECT_PANEL)
    bpy.utils.unregister_class(WaterProperties)
    bpy.utils.unregister_class(OT_Import_WaterXML)
    bpy.utils.unregister_class(OT_Export_WaterXML)
