import bpy
import gpu
import math
from gpu_extras.batch import batch_for_shader
from mathutils import Vector, Matrix


_draw_handler = None
_importing = False

# Colors
COLOR_INACTIVE = (0.55, 0.55, 0.55, 0.7)
COLOR_ACTIVE_SHAFT = (1.0, 1.0, 1.0, 0.95)
COLOR_ACTIVE_HEAD = (1.0, 1.0, 1.0, 0.95)


# Base units per amplitude unit – shared by arrow and amplitude gizmo
_AMP_RADIUS_BASE = 150.0
_AMP_RADIUS_MIN = 40.0

# Fixed radius for the direction ring (independent of amplitude)
_DIR_RING_RADIUS = 200.0


def get_amp_radius(amplitude):
    """Radius used for both the arrow length and the amplitude gizmo ring."""
    return max(_AMP_RADIUS_MIN, _AMP_RADIUS_BASE * amplitude)


def get_wave_quad_data():
    """Collect center, direction, amplitude and size for all wave quads."""
    quads = []
    for obj in bpy.data.objects:
        if obj.gta_quadtype != 'wave':
            continue
        if not obj.data or not hasattr(obj.data, 'vertices') or len(obj.data.vertices) < 3:
            continue

        # Compute world-space bounding box center and size
        coords = [obj.matrix_world @ v.co for v in obj.data.vertices]
        center = sum(coords, Vector((0, 0, 0))) / len(coords)

        xs = [c.x for c in coords]
        ys = [c.y for c in coords]
        quad_size = max(max(xs) - min(xs), max(ys) - min(ys))

        amp = obj.waterProperties.water_amplitude
        dx = obj.waterProperties.water_xDirection
        dy = obj.waterProperties.water_yDirection

        quads.append((obj, center, dx, dy, amp, quad_size))
    return quads


def build_arrow_verts(center, dx, dy, amplitude):
    """Build line vertices for an arrow: shaft + two arrowhead wings."""
    length = get_amp_radius(amplitude)
    head_size = length * 0.3

    direction = Vector((dx, dy, 0.0))
    if direction.length < 0.0001:
        return [], []

    direction.normalize()
    tip = center + direction * length
    perp = Vector((-direction.y, direction.x, 0.0))

    # Shaft
    shaft = [center, tip]

    # Arrowhead wings
    wing1 = tip - direction * head_size + perp * head_size * 0.5
    wing2 = tip - direction * head_size - perp * head_size * 0.5
    head = [tip, wing1, tip, wing2]

    return shaft, head


def draw_wave_overlays():
    """GPU draw callback for wave direction arrows."""
    if _importing:
        return

    scene = bpy.context.scene
    if not getattr(scene, 'watereditor_show_wave_overlay', True):
        return

    quads = get_wave_quad_data()
    if not quads:
        return

    active_obj = bpy.context.active_object
    inactive_shaft = []
    inactive_head = []
    active_shaft = []
    active_head = []

    for obj, center, dx, dy, amp, quad_size in quads:
        s, h = build_arrow_verts(center, dx, dy, amp)
        if obj == active_obj:
            active_shaft.extend(s)
            active_head.extend(h)
        else:
            inactive_shaft.extend(s)
            inactive_head.extend(h)

    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    gpu.state.blend_set('ALPHA')

    # Draw inactive arrows
    gpu.state.line_width_set(2.0)
    if inactive_shaft:
        batch = batch_for_shader(shader, 'LINES', {"pos": inactive_shaft})
        shader.uniform_float("color", COLOR_INACTIVE)
        batch.draw(shader)
    if inactive_head:
        batch = batch_for_shader(shader, 'LINES', {"pos": inactive_head})
        shader.uniform_float("color", COLOR_INACTIVE)
        batch.draw(shader)

    # Draw active arrow (brighter, thicker)
    gpu.state.line_width_set(4.0)
    if active_shaft:
        batch = batch_for_shader(shader, 'LINES', {"pos": active_shaft})
        shader.uniform_float("color", COLOR_ACTIVE_SHAFT)
        batch.draw(shader)
    if active_head:
        batch = batch_for_shader(shader, 'LINES', {"pos": active_head})
        shader.uniform_float("color", COLOR_ACTIVE_HEAD)
        batch.draw(shader)

    gpu.state.line_width_set(1.0)
    gpu.state.blend_set('NONE')


def _quad_center_and_size(obj):
    """Compute world-space center and size of a quad object."""
    coords = [obj.matrix_world @ v.co for v in obj.data.vertices]
    center = sum(coords, Vector((0, 0, 0))) / len(coords)
    xs = [c.x for c in coords]
    ys = [c.y for c in coords]
    quad_size = max(max(xs) - min(xs), max(ys) - min(ys))
    return center, quad_size


class WATEREDITOR_GGT_wave_direction(bpy.types.GizmoGroup):
    bl_idname = "WATEREDITOR_GGT_wave_direction"
    bl_label = "Wave Direction"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D', 'PERSISTENT', 'SHOW_MODAL_ALL'}

    @classmethod
    def poll(cls, context):
        if not getattr(context.scene, 'watereditor_show_wave_overlay', True):
            return False
        obj = context.active_object
        return (obj is not None
                and getattr(obj, 'gta_quadtype', None) == 'wave'
                and obj.data is not None
                and hasattr(obj.data, 'vertices')
                and len(obj.data.vertices) >= 3)

    def setup(self, context):
        # Direction dial (white)
        gz = self.gizmos.new("GIZMO_GT_dial_3d")
        gz.draw_options = {'CLIP'}
        gz.use_draw_modal = True
        gz.use_draw_scale = False
        gz.color = 0.85, 0.85, 0.85
        gz.alpha = 0.4
        gz.color_highlight = 1.0, 1.0, 1.0
        gz.alpha_highlight = 0.7
        gz.line_width = 4.0

        gz.target_set_handler(
            "offset",
            get=self._get_angle,
            set=self._set_angle,
        )
        self.dial_gizmo = gz

        # Amplitude dial (blue)
        amp = self.gizmos.new("GIZMO_GT_dial_3d")
        amp.draw_options = {'CLIP'}
        amp.use_draw_modal = True
        amp.use_draw_scale = False
        amp.color = 0.2, 0.55, 1.0
        amp.alpha = 0.45
        amp.color_highlight = 0.4, 0.75, 1.0
        amp.alpha_highlight = 0.8
        amp.line_width = 4.0

        amp.target_set_handler(
            "offset",
            get=self._get_amplitude,
            set=self._set_amplitude,
        )
        self.amp_gizmo = amp

        self._update_gizmo(context)

    def _get_angle(self):
        obj = bpy.context.active_object
        if not obj or obj.gta_quadtype != 'wave':
            return 0.0
        dx = obj.waterProperties.water_xDirection
        dy = obj.waterProperties.water_yDirection
        return -math.atan2(dy, dx)

    def _set_angle(self, value):
        obj = bpy.context.active_object
        if not obj or obj.gta_quadtype != 'wave':
            return
        obj.waterProperties.water_xDirection = math.cos(-value)
        obj.waterProperties.water_yDirection = math.sin(-value)
        # Force viewport redraw so the arrow follows in real-time
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()

    def _get_amplitude(self):
        obj = bpy.context.active_object
        if not obj or obj.gta_quadtype != 'wave':
            return 0.0
        return obj.waterProperties.water_amplitude

    def _set_amplitude(self, value):
        obj = bpy.context.active_object
        if not obj or obj.gta_quadtype != 'wave':
            return
        obj.waterProperties.water_amplitude = max(0.01, value)
        # Force viewport redraw so the arrow length follows in real-time
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()

    def _update_gizmo(self, context):
        obj = context.active_object
        if not obj or obj.gta_quadtype != 'wave':
            return
        if not obj.data or len(obj.data.vertices) < 3:
            return

        center, quad_size = _quad_center_and_size(obj)

        # Lift slightly above the quad so the dials are visible
        center.z += 1.0

        # Direction ring – fixed size, independent of amplitude
        mat_dir = Matrix.Translation(center) @ Matrix.Scale(_DIR_RING_RADIUS, 4)
        self.dial_gizmo.matrix_basis = mat_dir

        # Amplitude ring – radius matches arrow tip distance
        amp_val = obj.waterProperties.water_amplitude
        amp_scale = get_amp_radius(amp_val)
        mat_amp = Matrix.Translation(center) @ Matrix.Scale(amp_scale, 4)
        self.amp_gizmo.matrix_basis = mat_amp

    def refresh(self, context):
        self._update_gizmo(context)

    def draw_prepare(self, context):
        self._update_gizmo(context)


def register_overlay():
    global _draw_handler
    if _draw_handler is not None:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(_draw_handler, 'WINDOW')
        except Exception:
            pass
    _draw_handler = bpy.types.SpaceView3D.draw_handler_add(
        draw_wave_overlays, (), 'WINDOW', 'POST_VIEW'
    )
    bpy.utils.register_class(WATEREDITOR_GGT_wave_direction)


def unregister_overlay():
    global _draw_handler
    if _draw_handler is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_draw_handler, 'WINDOW')
        _draw_handler = None
    bpy.utils.unregister_class(WATEREDITOR_GGT_wave_direction)
