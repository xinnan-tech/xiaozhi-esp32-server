// Read fonts - ES6 version for browser
// 核心字体数据收集模块

import opentype from 'opentype.js'
import * as ft_render from './FreeType.js'
import AppError from './AppError.js' 
import Ranger from './Ranger.js'

export default async function collect_font_data(args) {
  await ft_render.init()

  // Duplicate font options as k/v for quick access
  let fonts_options = {}
  args.font.forEach(f => { fonts_options[f.source_path] = f })

  // read fonts
  let fonts_opentype = {}
  let fonts_freetype = {}

  for (let { source_path, source_bin } of args.font) {
    // don't load font again if it's specified multiple times in args
    if (fonts_opentype[source_path]) continue

    try {
      let b = source_bin

      // 处理不同类型的输入数据
      if (b instanceof File) {
        b = await b.arrayBuffer()
      } else if (b instanceof Uint8Array) {
        // Uint8Array
        b = b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength)
      }

      fonts_opentype[source_path] = opentype.parse(b)
      
      // 使用处理后的数据创建 FreeType 字体实例
      fonts_freetype[source_path] = ft_render.fontface_create(b, args.size)
    } catch (err) {
      throw new AppError(`Cannot load font "${source_path}": ${err.message}`)
    }
  }

  // merge all ranges
  let ranger = new Ranger()

  for (let { source_path, ranges } of args.font) {
    let font = fonts_freetype[source_path]

    for (let item of ranges) {
      /* eslint-disable max-depth */
      if (item.range) {
        for (let i = 0; i < item.range.length; i += 3) {
          let range = item.range.slice(i, i + 3)
          let chars = ranger.add_range(source_path, ...range)
          let is_empty = true

          for (let code of chars) {
            if (ft_render.glyph_exists(font, code)) {
              is_empty = false
              break
            }
          }

          if (is_empty) {
            let a = '0x' + range[0].toString(16)
            let b = '0x' + range[1].toString(16)
            throw new AppError(`Font "${source_path}" doesn't have any characters included in range ${a}-${b}`)
          }
        }
      }

      if (item.symbols) {
        let chars = ranger.add_symbols(source_path, item.symbols)
        let is_empty = true

        for (let code of chars) {
          if (ft_render.glyph_exists(font, code)) {
            is_empty = false
            break
          }
        }

        if (is_empty) {
          throw new AppError(`Font "${source_path}" doesn't have any characters included in "${item.symbols}"`)
        }
      }
    }
  }

  let mapping = ranger.get()
  let glyphs = []
  let all_dst_charcodes = Object.keys(mapping).sort((a, b) => a - b).map(Number)

  for (let dst_code of all_dst_charcodes) {
    let src_code = mapping[dst_code].code
    let src_font = mapping[dst_code].font

    if (!ft_render.glyph_exists(fonts_freetype[src_font], src_code)) continue

    let ft_result = ft_render.glyph_render(
      fonts_freetype[src_font],
      src_code,
      {
        autohint_off: fonts_options[src_font].autohint_off,
        autohint_strong: fonts_options[src_font].autohint_strong,
        lcd: args.lcd,
        lcd_v: args.lcd_v,
        mono: !args.lcd && !args.lcd_v && args.bpp === 1,
        use_color_info: args.use_color_info
      }
    )

    glyphs.push({
      code: dst_code,
      advanceWidth: ft_result.advance_x,
      bbox: {
        x: ft_result.x,
        y: ft_result.y - ft_result.height,
        width: ft_result.width,
        height: ft_result.height
      },
      kerning: {},
      freetype: ft_result.freetype,
      pixels: ft_result.pixels
    })
  }

  if (!args.no_kerning) {
    let existing_dst_charcodes = glyphs.map(g => g.code)

    for (let { code, kerning } of glyphs) {
      let src_code = mapping[code].code
      let src_font = mapping[code].font
      let font     = fonts_opentype[src_font]
      let glyph    = font.charToGlyph(String.fromCodePoint(src_code))

      for (let dst_code2 of existing_dst_charcodes) {
        // can't merge kerning values from 2 different fonts
        if (mapping[dst_code2].font !== src_font) continue

        let src_code2 = mapping[dst_code2].code
        let glyph2 = font.charToGlyph(String.fromCodePoint(src_code2))
        let krn_value = font.getKerningValue(glyph, glyph2)

        if (krn_value) kerning[dst_code2] = krn_value * args.size / font.unitsPerEm

        //let krn_value = ft_render.get_kerning(font, src_code, src_code2).x;
        //if (krn_value) kerning[dst_code2] = krn_value;
      }
    }
  }

  let first_font = fonts_freetype[args.font[0].source_path]
  let first_font_scale = args.size / first_font.units_per_em
  let os2_metrics = ft_render.fontface_os2_table(first_font)
  let post_table = fonts_opentype[args.font[0].source_path].tables.post

  for (let font of Object.values(fonts_freetype)) ft_render.fontface_destroy(font)

  ft_render.destroy()

  return {
    ascent:      Math.max(...glyphs.map(g => g.bbox.y + g.bbox.height)),
    descent:     Math.min(...glyphs.map(g => g.bbox.y)),
    typoAscent:  Math.round(os2_metrics.typoAscent * first_font_scale),
    typoDescent: Math.round(os2_metrics.typoDescent * first_font_scale),
    typoLineGap: Math.round(os2_metrics.typoLineGap * first_font_scale),
    size:        args.size,
    glyphs,
    underlinePosition:  Math.round(post_table.underlinePosition * first_font_scale),
    underlineThickness: Math.round(post_table.underlineThickness * first_font_scale)
  }
}
