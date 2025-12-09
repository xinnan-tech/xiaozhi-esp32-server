// FreeType interface for browser
// ES6 版本，适配浏览器环境

const ft_render_fabric = () => import('./freetype_build/ft_render.js')

let m = null     // compiled module instance
let library = 0  // pointer to library struct in wasm memory

// workaround because of bug in emscripten:
// https://github.com/emscripten-core/emscripten/issues/5820
const runtime_initialized = new Promise(resolve => {
  ft_render_fabric().then(module => {
    module.default().then(module_instance => {
      m = module_instance
      resolve()
    })
  })
})

function from_16_16(fixed_point) {
  return fixed_point / (1 << 16)
}

function from_26_6(fixed_point) {
  return fixed_point / (1 << 6)
}

function int8_to_uint8(value) {
  return value >= 0 ? value : value + 0x100
}

let FT_New_Memory_Face,
    FT_Set_Char_Size,
    FT_Set_Pixel_Sizes,
    FT_Get_Char_Index,
    FT_Load_Glyph,
    FT_Get_Sfnt_Table,
    FT_Get_Kerning,
    FT_Done_Face

export async function init() {
  await runtime_initialized
  m._init_constants()

  FT_New_Memory_Face = 
    m.cwrap('FT_New_Memory_Face', 'number', [ 'number', 'number', 'number', 'number', 'number' ])

  FT_Set_Char_Size = 
    m.cwrap('FT_Set_Char_Size', 'number', [ 'number', 'number', 'number', 'number', 'number' ])

  FT_Set_Pixel_Sizes = 
    m.cwrap('FT_Set_Pixel_Sizes', 'number', [ 'number', 'number', 'number' ])

  FT_Get_Char_Index = 
    m.cwrap('FT_Get_Char_Index', 'number', [ 'number', 'number' ])

  FT_Load_Glyph = 
    m.cwrap('FT_Load_Glyph', 'number', [ 'number', 'number', 'number' ])

  FT_Get_Sfnt_Table = 
    m.cwrap('FT_Get_Sfnt_Table', 'number', [ 'number', 'number' ])

  FT_Get_Kerning = 
    m.cwrap('FT_Get_Kerning', 'number', [ 'number', 'number', 'number', 'number', 'number' ])

  FT_Done_Face = 
    m.cwrap('FT_Done_Face', 'number', [ 'number' ])

  if (!library) {
    let ptr = m._malloc(4)

    try {
      let error = m.ccall('FT_Init_FreeType', 'number', [ 'number' ], [ ptr ])

      if (error) throw new Error(`error in FT_Init_FreeType: ${error}`)

      library = m.getValue(ptr, 'i32')
    } finally {
      m._free(ptr)
    }
  }
}

export function fontface_create(source, size) {
  let error
  
  // 正确计算字体数据的长度
  let fontLength
  if (source instanceof ArrayBuffer) {
    fontLength = source.byteLength
  } else if (source instanceof Uint8Array) {
    fontLength = source.byteLength
  } else if (source && typeof source.length === 'number') {
    fontLength = source.length
  } else {
    throw new Error('Invalid font source format')
  }
  
  let face = {
    ptr: 0,
    font: m._malloc(fontLength)
  }

  // 将 ArrayBuffer 或 Uint8Array 转换为内存
  const sourceArray = source instanceof ArrayBuffer ? new Uint8Array(source) : source
  m.writeArrayToMemory(sourceArray, face.font)

  let ptr = m._malloc(4)

  try {
    error = FT_New_Memory_Face(library, face.font, fontLength, 0, ptr)

    if (error) throw new Error(`error in FT_New_Memory_Face: ${error}`)

    face.ptr = m.getValue(ptr, 'i32')
  } finally {
    m._free(ptr)
  }

  error = FT_Set_Char_Size(face.ptr, 0, size * 64, 300, 300)

  if (error) throw new Error(`error in FT_Set_Char_Size: ${error}`)

  error = FT_Set_Pixel_Sizes(face.ptr, 0, size)

  if (error) throw new Error(`error in FT_Set_Pixel_Sizes: ${error}`)

  let units_per_em = m.getValue(face.ptr + m.OFFSET_FACE_UNITS_PER_EM, 'i16')
  let ascender     = m.getValue(face.ptr + m.OFFSET_FACE_ASCENDER, 'i16')
  let descender    = m.getValue(face.ptr + m.OFFSET_FACE_DESCENDER, 'i16')
  let height       = m.getValue(face.ptr + m.OFFSET_FACE_HEIGHT, 'i16')

  return Object.assign(face, {
    units_per_em,
    ascender,
    descender,
    height
  })
}

export function fontface_os2_table(face) {
  let sfnt_ptr = FT_Get_Sfnt_Table(face.ptr, m.FT_SFNT_OS2)

  if (!sfnt_ptr) throw new Error('os/2 table not found for this font')

  let typoAscent  = m.getValue(sfnt_ptr + m.OFFSET_TT_OS2_ASCENDER, 'i16')
  let typoDescent = m.getValue(sfnt_ptr + m.OFFSET_TT_OS2_DESCENDER, 'i16')
  let typoLineGap = m.getValue(sfnt_ptr + m.OFFSET_TT_OS2_LINEGAP, 'i16')

  return {
    typoAscent,
    typoDescent,
    typoLineGap
  }
}

export function get_kerning(face, code1, code2) {
  let glyph1 = FT_Get_Char_Index(face.ptr, code1)
  let glyph2 = FT_Get_Char_Index(face.ptr, code2)
  let ptr = m._malloc(4 * 2)

  try {
    let error = FT_Get_Kerning(face.ptr, glyph1, glyph2, m.FT_KERNING_DEFAULT, ptr)

    if (error) throw new Error(`error in FT_Get_Kerning: ${error}`)
    
    return {
      x: from_26_6(m.getValue(ptr, 'i32')),
      y: from_26_6(m.getValue(ptr + 4, 'i32'))
    }
  } finally {
    m._free(ptr)
  }
}

export function glyph_exists(face, code) {
  let glyph_index = FT_Get_Char_Index(face.ptr, code)

  return glyph_index !== 0
}

export function glyph_render(face, code, opts = {}) {
  let glyph_index = FT_Get_Char_Index(face.ptr, code)

  if (glyph_index === 0) throw new Error(`glyph does not exist for codepoint ${code}`)

  let load_flags = m.FT_LOAD_RENDER

  if (opts.mono) {
    load_flags |= m.FT_LOAD_TARGET_MONO

  } else if (opts.lcd) {
    load_flags |= m.FT_LOAD_TARGET_LCD

  } else if (opts.lcd_v) {
    load_flags |= m.FT_LOAD_TARGET_LCD_V

  } else {
    /* eslint-disable no-lonely-if */

    // Use "light" by default, it changes horizontal lines only.
    // "normal" is more strong (with vertical lines), but will break kerning, if
    // no additional care taken. More advanced rendering requires upper level
    // layout support (via Harfbuzz, for example).
    if (!opts.autohint_strong) load_flags |= m.FT_LOAD_TARGET_LIGHT
    else load_flags |= m.FT_LOAD_TARGET_NORMAL
  }

  if (opts.autohint_off) load_flags |= m.FT_LOAD_NO_AUTOHINT
  else load_flags |= m.FT_LOAD_FORCE_AUTOHINT

  if (opts.use_color_info) load_flags |= m.FT_LOAD_COLOR

  let error = FT_Load_Glyph(face.ptr, glyph_index, load_flags)

  if (error) throw new Error(`error in FT_Load_Glyph: ${error}`)

  let glyph = m.getValue(face.ptr + m.OFFSET_FACE_GLYPH, 'i32')

  let glyph_data = {
    glyph_index: m.getValue(glyph + m.OFFSET_GLYPH_INDEX, 'i32'),
    metrics: {
      width:        from_26_6(m.getValue(glyph + m.OFFSET_GLYPH_METRICS_WIDTH, 'i32')),
      height:       from_26_6(m.getValue(glyph + m.OFFSET_GLYPH_METRICS_HEIGHT, 'i32')),
      horiBearingX: from_26_6(m.getValue(glyph + m.OFFSET_GLYPH_METRICS_HORI_BEARING_X, 'i32')),
      horiBearingY: from_26_6(m.getValue(glyph + m.OFFSET_GLYPH_METRICS_HORI_BEARING_Y, 'i32')),
      horiAdvance:  from_26_6(m.getValue(glyph + m.OFFSET_GLYPH_METRICS_HORI_ADVANCE, 'i32')),
      vertBearingX: from_26_6(m.getValue(glyph + m.OFFSET_GLYPH_METRICS_VERT_BEARING_X, 'i32')),
      vertBearingY: from_26_6(m.getValue(glyph + m.OFFSET_GLYPH_METRICS_VERT_BEARING_Y, 'i32')),
      vertAdvance:  from_26_6(m.getValue(glyph + m.OFFSET_GLYPH_METRICS_VERT_ADVANCE, 'i32'))
    },
    linearHoriAdvance: from_16_16(m.getValue(glyph + m.OFFSET_GLYPH_LINEAR_HORI_ADVANCE, 'i32')),
    linearVertAdvance: from_16_16(m.getValue(glyph + m.OFFSET_GLYPH_LINEAR_VERT_ADVANCE, 'i32')),
    advance: {
      x: from_26_6(m.getValue(glyph + m.OFFSET_GLYPH_ADVANCE_X, 'i32')),
      y: from_26_6(m.getValue(glyph + m.OFFSET_GLYPH_ADVANCE_Y, 'i32'))
    },
    bitmap: {
      width:        m.getValue(glyph + m.OFFSET_GLYPH_BITMAP_WIDTH, 'i32'),
      rows:         m.getValue(glyph + m.OFFSET_GLYPH_BITMAP_ROWS, 'i32'),
      pitch:        m.getValue(glyph + m.OFFSET_GLYPH_BITMAP_PITCH, 'i32'),
      num_grays:    m.getValue(glyph + m.OFFSET_GLYPH_BITMAP_NUM_GRAYS, 'i16'),
      pixel_mode:   m.getValue(glyph + m.OFFSET_GLYPH_BITMAP_PIXEL_MODE, 'i8'),
      palette_mode: m.getValue(glyph + m.OFFSET_GLYPH_BITMAP_PALETTE_MODE, 'i8')
    },
    bitmap_left: m.getValue(glyph + m.OFFSET_GLYPH_BITMAP_LEFT, 'i32'),
    bitmap_top:  m.getValue(glyph + m.OFFSET_GLYPH_BITMAP_TOP, 'i32'),
    lsb_delta:   from_26_6(m.getValue(glyph + m.OFFSET_GLYPH_LSB_DELTA, 'i32')),
    rsb_delta:   from_26_6(m.getValue(glyph + m.OFFSET_GLYPH_RSB_DELTA, 'i32'))
  }

  let g_w = glyph_data.bitmap.width
  let g_h = glyph_data.bitmap.rows
  let g_x = glyph_data.bitmap_left
  let g_y = glyph_data.bitmap_top

  let buffer = m.getValue(glyph + m.OFFSET_GLYPH_BITMAP_BUFFER, 'i32')
  let pitch  = Math.abs(glyph_data.bitmap.pitch)

  let advance_x = glyph_data.linearHoriAdvance
  let advance_y = glyph_data.linearVertAdvance

  let pixel_mode = glyph_data.bitmap.pixel_mode

  let output = []

  for (let y = 0; y < g_h; y++) {
    let row_start = buffer + y * pitch
    let line = []

    for (let x = 0; x < g_w; x++) {
      if (pixel_mode === m.FT_PIXEL_MODE_MONO) {
        let value = m.getValue(row_start + ~~(x / 8), 'i8')
        line.push(value & (1 << (7 - (x % 8))) ? 255 : 0)
      } else if (pixel_mode === m.FT_PIXEL_MODE_BGRA) {
        let blue  = int8_to_uint8(m.getValue(row_start + (x * 4) + 0, 'i8'))
        let green = int8_to_uint8(m.getValue(row_start + (x * 4) + 1, 'i8'))
        let red   = int8_to_uint8(m.getValue(row_start + (x * 4) + 2, 'i8'))
        let alpha = int8_to_uint8(m.getValue(row_start + (x * 4) + 3, 'i8'))
        // convert RGBA to grayscale
        let grayscale = Math.round(0.299 * red + 0.587 * green + 0.114 * blue)
        if (grayscale > 255) grayscale = 255
        // meld grayscale into alpha channel
        alpha = ((255 - grayscale) * alpha) / 255
        line.push(alpha)
      } else {
        let value = m.getValue(row_start + x, 'i8')
        line.push(int8_to_uint8(value))
      }
    }

    output.push(line)
  }

  return {
    x: g_x,
    y: g_y,
    width: g_w,
    height: g_h,
    advance_x,
    advance_y,
    pixels: output,
    freetype: glyph_data
  }
}

export function fontface_destroy(face) {
  let error = FT_Done_Face(face.ptr)

  if (error) throw new Error(`error in FT_Done_Face: ${error}`)

  m._free(face.font)
  face.ptr = 0
  face.font = 0
}

export function destroy() {
  let error = m.ccall('FT_Done_FreeType', 'number', [ 'number' ], [ library ])

  if (error) throw new Error(`error in FT_Done_FreeType: ${error}`)

  library = 0

  // don't unload wasm - slows down tests too much
  //m = null
}