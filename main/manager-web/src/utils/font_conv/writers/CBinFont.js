// CBIN Font writer - 严格按照官方实现（浏览器兼容版）
// 遵循 font_conv_lib/writers/cbin/ 的格式

import AppError from '../AppError.js';
import cmap_build_subtables from '../cmap_build_subtables.js';

// 32位指针大小，保持与官方一致
const ptr_size = 4;

// 浏览器版本的 writeUInt64LE 实现
const writeUInt64LE = (view, val, pos) => {
  view.setUint32(pos, val, true);
  view.setUint32(pos + 4, 0, true);
};

class CBinFont {
  constructor(fontData, options) {
    this.src = fontData;
    this.opts = options;

    this.font_name = options.lv_font_name;
    if (!this.font_name) {
      this.font_name = options.output || 'font';
    }

    if (options.bpp === 3 && options.no_compress) {
      throw new AppError('LVGL supports "--bpp 3" with compression only');
    }

    // 初始化各个表格处理器
    this.init_tables();
  }

  init_tables() {
    this.head = new HeadTable(this);
    this.glyf = new GlyfTable(this); 
    this.cmap = new CmapTable(this);
    this.kern = new KernTable(this);
  }

  toCBin() {
    // 严格按照 lv_font.js 的实现（浏览器兼容版）
    const [bitmap_buf, glyph_dsc_buf] = this.glyf.toCBin();
    const cmaps_buf = this.cmap.toCBin(ptr_size);
    const kern_buf = this.kern.toCBin(ptr_size);
    
    const sz_font = 12 + ptr_size * 6 + (ptr_size == 4 ? 0 : 4); // add pad, see below
    const sz_font_dsc = 8 + ptr_size * 4; // add space for stride
    const head_buf = new ArrayBuffer(sz_font + sz_font_dsc);
    const head_view = new DataView(head_buf);

    const writePTR = ptr_size == 4 ? 
      (val, pos) => head_view.setUint32(pos, val, true) : 
      (val, pos) => writeUInt64LE(head_view, val, pos);

    var pos = 0;
    // write lv_font_t 
    writePTR(0, pos); pos += ptr_size;
    writePTR(0, pos); pos += ptr_size;
    writePTR(0, pos); pos += ptr_size;
    head_view.setUint32(pos, this.src.ascent - this.src.descent, true); pos += 4; // line_height
    head_view.setInt32(pos, -this.src.descent, true); pos += 4; // base_line

    head_view.setUint8(pos, this.src.subpixels_mode || 0); pos += 1;
    head_view.setInt8(pos, this.src.underlinePosition || 0); pos += 1;
    head_view.setInt8(pos, this.src.underlineThickness || 0); pos += 1;
    pos += 1 + (ptr_size == 4 ? 0 : 4); // pad

    writePTR(sz_font, pos); pos += ptr_size; // offset relative to start of lv_font_t
    writePTR(0, pos); pos += ptr_size;
    writePTR(0, pos); pos += ptr_size;
    
    const kern = this.head.kern_ref();
    // write lv_font_fmt_txt_dsc_t
    writePTR(sz_font_dsc + kern_buf.byteLength, pos); pos += ptr_size;  // glyph_bitmap offset relative to start of lv_font_fmt_txt_dsc_t
    writePTR(sz_font_dsc + kern_buf.byteLength + bitmap_buf.byteLength, pos); pos += ptr_size;  // glyph_dsc ofs
    writePTR(sz_font_dsc + kern_buf.byteLength + bitmap_buf.byteLength + glyph_dsc_buf.byteLength, pos); pos += ptr_size;  // cmaps ofs
    writePTR(kern.dsc === 'NULL' ? 0 : sz_font_dsc, pos); pos += ptr_size; // kern ofs
    head_view.setUint16(pos, kern.scale, true); pos += 2;

    const cmap_num = this.cmap.getMapNumber();
    const bpp = this.opts.bpp;
    const kern_classes = kern.classes;
    const bitmap_format = this.glyf.getCompressionCode();
    head_view.setUint16(pos, cmap_num | (bpp << 9) | (kern_classes << (9 + 4)) | (bitmap_format << (9 + 4 + 1)), true); pos += 2;

    return this.concatArrayBuffers([
      head_buf,
      kern_buf,
      bitmap_buf,
      glyph_dsc_buf,
      cmaps_buf
    ]);
  }

  concatArrayBuffers(buffers) {
    // 浏览器兼容的 ArrayBuffer 合并方法
    const totalLength = buffers.reduce((sum, buf) => sum + buf.byteLength, 0);
    const result = new ArrayBuffer(totalLength);
    const view = new Uint8Array(result);
    
    let offset = 0;
    for (const buf of buffers) {
      view.set(new Uint8Array(buf), offset);
      offset += buf.byteLength;
    }
    
    return result;
  }
}

// 各个表格处理类的实现

// Head 表格处理器
class HeadTable {
  constructor(font) {
    this.font = font;
  }

  kern_ref() {
    const f = this.font;
    
    // 简化版：不支持 kerning
    return {
      scale: 0,
      dsc: 'NULL', 
      classes: 0
    };
  }
}

// 浏览器兼容的简化 BitStream 实现
class SimpleBitStream {
  constructor(buffer) {
    this.buffer = new Uint8Array(buffer);
    this.byteIndex = 0;
    this.bitIndex = 0;
    this.bigEndian = true;
  }

  writeBits(value, bits) {
    while (bits > 0) {
      const bitsToWrite = Math.min(8 - this.bitIndex, bits);
      const mask = (1 << bitsToWrite) - 1;
      const bitValue = (value >> (bits - bitsToWrite)) & mask;
      
      if (this.bigEndian) {
        this.buffer[this.byteIndex] |= (bitValue << (8 - this.bitIndex - bitsToWrite));
      } else {
        this.buffer[this.byteIndex] |= (bitValue << this.bitIndex);
      }
      
      this.bitIndex += bitsToWrite;
      if (this.bitIndex >= 8) {
        this.byteIndex++;
        this.bitIndex = 0;
      }
      
      bits -= bitsToWrite;
    }
  }

  getUsedBytes() {
    return this.bitIndex > 0 ? this.byteIndex + 1 : this.byteIndex;
  }
}

// Glyf 表格处理器 - 严格按照官方 lv_table_glyf.js 实现
class GlyfTable {
  constructor(font) {
    this.font = font;
    this.lv_data = [];
    this.lv_compiled = false;
  }

  // 严格按照官方 table_glyf.js 的 pixelsToBpp 实现
  pixelsToBpp(pixels) {
    const bpp = this.font.opts.bpp;
    return pixels.map(line => line.map(p => (p >>> (8 - bpp))));
  }

  // 严格按照官方的 storePixels 实现
  storePixels(bitStream, pixels) {
    if (this.getCompressionCode() === 0) this.storePixelsRaw(bitStream, pixels);
    else this.storePixelsCompressed(bitStream, pixels);
  }

  storePixelsRaw(bitStream, pixels) {
    const bpp = this.font.opts.bpp;

    for (let y = 0; y < pixels.length; y++) {
      const line = pixels[y];
      for (let x = 0; x < line.length; x++) {
        bitStream.writeBits(line[x], bpp);
      }
    }
  }

  storePixelsCompressed(bitStream, pixels) {
    // 简化版：暂不支持压缩，直接调用 raw 版本
    this.storePixelsRaw(bitStream, pixels);
  }

  lv_bitmap(glyph) {
    // 严格按照官方实现
    const bufSize = 100 + glyph.bbox.width * glyph.bbox.height * 4;
    const buf = new ArrayBuffer(bufSize);
    const bs = new SimpleBitStream(buf);
    bs.bigEndian = true;

    const pixels = this.pixelsToBpp(glyph.pixels);
    this.storePixels(bs, pixels);

    // 创建实际使用的 buffer
    const glyph_bitmap = new ArrayBuffer(bs.getUsedBytes());
    const srcView = new Uint8Array(buf);
    const destView = new Uint8Array(glyph_bitmap);
    destView.set(srcView.subarray(0, bs.getUsedBytes()));

    return glyph_bitmap;
  }

  lv_compile() {
    if (this.lv_compiled) return;

    this.lv_compiled = true;

    const f = this.font;
    this.lv_data = [];
    let offset = 0;

    // 严格按照官方逻辑：使用 f.glyph_id[g.code] 作为索引
    f.src.glyphs.forEach(g => {
      const id = f.glyph_id[g.code];
      const bin = this.lv_bitmap(g);
      this.lv_data[id] = {
        bin,
        offset,
        glyph: g
      };
      offset += bin.byteLength;
    });
  }

  toCBin() {
    // LV_FONT_FMT_TXT_LARGE == 1
    this.lv_compile();
    
    // 严格按照官方实现：slice(1) 跳过索引0，然后过滤有效数据
    const validBins = this.lv_data.slice(1).filter(d => d).map(d => d.bin);
    const bitmap_buf = this.balign4(this.concatArrayBuffers(validBins));
    const glyph_dsc_buf = new ArrayBuffer(this.lv_data.length * 16 + 16);
    const glyph_dsc_view = new DataView(glyph_dsc_buf);
    
    let i = 1;
    this.lv_data.forEach(d => {
      if (d) {
        const adv_w = Math.round(d.glyph.advanceWidth * 16);
        glyph_dsc_view.setUint32(i * 16, d.offset, true);
        glyph_dsc_view.setUint32(i * 16 + 4, adv_w, true);
        glyph_dsc_view.setUint16(i * 16 + 8, d.glyph.bbox.width, true);
        glyph_dsc_view.setUint16(i * 16 + 10, d.glyph.bbox.height, true);
        glyph_dsc_view.setInt16(i * 16 + 12, d.glyph.bbox.x, true);
        glyph_dsc_view.setInt16(i * 16 + 14, d.glyph.bbox.y, true);
      }
      i++;
    });
    
    return [bitmap_buf, glyph_dsc_buf];
  }

  balign4(buf) {
    const remainder = buf.byteLength % 4;
    if (remainder === 0) return buf;
    const padding = 4 - remainder;
    const paddingBuf = new ArrayBuffer(padding);
    return this.concatArrayBuffers([buf, paddingBuf]);
  }

  concatArrayBuffers(buffers) {
    const totalLength = buffers.reduce((sum, buf) => sum + buf.byteLength, 0);
    const result = new ArrayBuffer(totalLength);
    const view = new Uint8Array(result);
    
    let offset = 0;
    for (const buf of buffers) {
      view.set(new Uint8Array(buf), offset);
      offset += buf.byteLength;
    }
    
    return result;
  }

  getCompressionCode() {
    if (this.font.opts.no_compress) return 0;
    if (this.font.opts.bpp === 1) return 0;

    if (this.font.opts.no_prefilter) return 2;
    return 1;
  }
}

// Cmap 表格处理器 - 严格按照官方 lv_table_cmap.js 实现
class CmapTable {
  constructor(font) {
    this.font = font;
    this.lv_compiled = false;
    this.lv_subtables = [];
    this.subtables_plan = null;
    
    // 建立字形ID映射，按照官方逻辑
    this.buildGlyphIdMap();
  }

  buildGlyphIdMap() {
    const f = this.font;
    f.glyph_id = {};
    
    if (f.src.glyphs) {
      f.src.glyphs.forEach((glyph, index) => {
        f.glyph_id[glyph.code] = index + 1; // 字形ID从1开始
      });
    }
  }

  lv_format2enum(name) {
    switch (name) {
      case 'format0_tiny': return 'LV_FONT_FMT_TXT_CMAP_FORMAT0_TINY';
      case 'format0': return 'LV_FONT_FMT_TXT_CMAP_FORMAT0_FULL';
      case 'sparse_tiny': return 'LV_FONT_FMT_TXT_CMAP_SPARSE_TINY';
      case 'sparse': return 'LV_FONT_FMT_TXT_CMAP_SPARSE_FULL';
      default: throw new Error('Unknown subtable format');
    }
  }

  lv_format2int(name) {
    return ['format0','sparse','format0_tiny','sparse_tiny'].indexOf(name);
  }

  getMapNumber() {
    // 返回子表数量，需要先确保已经生成了子表计划
    if (!this.subtables_plan) {
      const f = this.font;
      if (!f.src.glyphs || f.src.glyphs.length === 0) {
        return 0;
      }
      this.subtables_plan = cmap_build_subtables(f.src.glyphs.map(g => g.code));
    }
    return this.subtables_plan.length;
  }

  glyphByCode(code) {
    const f = this.font;
    return f.src.glyphs ? f.src.glyphs.find(g => g.code === code) : null;
  }

  collect_format0_data(min_code, max_code, start_glyph_id) {
    const f = this.font;
    const data = [];
    
    for (let code = min_code; code <= max_code; code++) {
      const glyph_id = f.glyph_id[code] || 0;
      // format0的数据格式是相对于start_glyph_id的偏移
      data.push(glyph_id ? glyph_id - start_glyph_id : 0);
    }
    
    return data;
  }

  collect_sparse_data(codepoints, start_glyph_id) {
    const f = this.font;
    let codepoints_list = [];
    let ids_list = [];

    for (let code of codepoints) {
      let g = this.glyphByCode(code);
      let id = f.glyph_id[g.code];

      let code_delta = code - codepoints[0];  // 关键：相对于第一个代码点的偏移
      let id_delta = id - start_glyph_id;

      if (code_delta < 0 || code_delta > 65535) throw new Error('Codepoint delta out of range');
      if (id_delta < 0 || id_delta > 65535) throw new Error('Glyph ID delta out of range');

      codepoints_list.push(code_delta);  // 推入 delta，不是原始 code
      ids_list.push(id_delta);
    }

    return {
      codes: codepoints_list,
      ids: ids_list
    };
  }

  toCBin(ptr_size) {
    const f = this.font;

    if (!f.src.glyphs || f.src.glyphs.length === 0) {
      return new ArrayBuffer(0);
    }

    // 确保只计算一次 subtables_plan
    if (!this.subtables_plan) {
      this.subtables_plan = cmap_build_subtables(f.src.glyphs.map(g => g.code));
    }
    const subtables_plan = this.subtables_plan;
    let idx = 0;

    const cmap_size = 12 + ptr_size * 2 + (ptr_size == 4 ? 0 : 4);
    const cmaps_buf = new ArrayBuffer(subtables_plan.length * cmap_size);
    const cmaps_view = new DataView(cmaps_buf);
    
    const writePTR = ptr_size == 4 ? 
      (val, ofs) => cmaps_view.setUint32(ofs, val, true) : 
      (val, ofs) => writeUInt64LE(cmaps_view, val, ofs);
    
    const arr_list = [];
    let total_data_offset = cmaps_buf.byteLength;

    for (let [format, codepoints] of subtables_plan) {
      let g = this.glyphByCode(codepoints[0]);
      let start_glyph_id = f.glyph_id[g.code];
      let min_code = codepoints[0];
      let max_code = codepoints[codepoints.length - 1];

      let has_charcodes = false;
      let has_ids = false;
      let entries_count = 0;

      let glyph_ptr = new ArrayBuffer(0);
      let unicode_ptr = new ArrayBuffer(0);

      if (format === 'format0_tiny') {
        // use default empty values
      } else if (format === 'format0') {
        has_ids = true;
        let d = this.collect_format0_data(min_code, max_code, start_glyph_id);
        entries_count = d.length;
        // 严格按照官方：Buffer.from(d)
        glyph_ptr = this.balign4(this.uint8ArrayToBuffer(new Uint8Array(d)));
      } else if (format === 'sparse_tiny') {
        has_charcodes = true;
        let d = this.collect_sparse_data(codepoints, start_glyph_id);
        entries_count = d.codes.length;
        unicode_ptr = this.balign4(this.uint16ArrayToBuffer(new Uint16Array(d.codes)));
      } else { // assume format === 'sparse'
        has_charcodes = true;
        has_ids = true;
        let d = this.collect_sparse_data(codepoints, start_glyph_id);
        entries_count = d.codes.length;
        unicode_ptr = this.balign4(this.uint16ArrayToBuffer(new Uint16Array(d.codes)));
        glyph_ptr = this.align4(this.uint16ArrayToBuffer(new Uint16Array(d.ids)));
      }

      // 写入 cmap 头部 - 严格按照官方逻辑
      let ofs = idx * cmap_size;
      cmaps_view.setUint32(ofs, min_code, true); ofs += 4;
      cmaps_view.setUint16(ofs, max_code - min_code + 1, true); ofs += 2;
      cmaps_view.setUint16(ofs, start_glyph_id, true); ofs += 2;
      // 关键：写入指针的同时立即更新 total_data_offset
      writePTR(has_charcodes ? total_data_offset : 0, ofs); ofs += ptr_size; 
      total_data_offset += unicode_ptr.byteLength;
      writePTR(has_ids ? total_data_offset : 0, ofs); ofs += ptr_size; 
      total_data_offset += glyph_ptr.byteLength;
      cmaps_view.setUint16(ofs, entries_count, true); ofs += 2;
      cmaps_view.setUint8(ofs, this.lv_format2int(format)); ofs += 1;

      arr_list.push(unicode_ptr);
      arr_list.push(glyph_ptr);

      idx++;
    }
    return this.concatArrayBuffers([cmaps_buf, ...arr_list]);
  }

  balign4(buf) {
    const remainder = buf.byteLength % 4;
    if (remainder === 0) return buf;
    const padding = 4 - remainder;
    const paddingBuf = new ArrayBuffer(padding);
    return this.concatArrayBuffers([buf, paddingBuf]);
  }

  align4(buf) {
    const remainder = buf.byteLength % 4;
    if (remainder === 0) return buf;
    const padding = 4 - remainder;
    const paddingBuf = new ArrayBuffer(padding);
    return this.concatArrayBuffers([buf, paddingBuf]);
  }

  uint8ArrayToBuffer(uint8Array) {
    const buffer = new ArrayBuffer(uint8Array.byteLength);
    const view = new Uint8Array(buffer);
    view.set(uint8Array);
    return buffer;
  }

  uint16ArrayToBuffer(uint16Array) {
    // 严格按照官方的处理方式：直接使用 Uint16Array 的 buffer
    // 这等价于官方的 Buffer.from(Uint16Array.from(d.codes).buffer)
    return uint16Array.buffer.slice(0, uint16Array.byteLength);
  }

  concatArrayBuffers(buffers) {
    const totalLength = buffers.reduce((sum, buf) => sum + buf.byteLength, 0);
    const result = new ArrayBuffer(totalLength);
    const view = new Uint8Array(result);
    
    let offset = 0;
    for (const buf of buffers) {
      view.set(new Uint8Array(buf), offset);
      offset += buf.byteLength;
    }
    
    return result;
  }
}

// Kern 表格处理器（简化版，不支持 kerning）
class KernTable {
  constructor(font) {
    this.font = font;
  }

  toCBin(ptr_size) {
    // 简化版：不支持 kerning，返回空 buffer
    return new ArrayBuffer(0);
  }
}

export default CBinFont;
