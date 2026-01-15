// Font processing utilities
// ES6 版本，适配浏览器环境

function set_byte_depth(depth) {
  return function (byte) {
    // calculate significant bits, e.g. for depth=2 it's 0, 1, 2 or 3
    let value = ~~(byte / (256 >> depth))

    // spread those bits around 0..255 range, e.g. for depth=2 it's 0, 85, 170 or 255
    let scale = (2 << (depth - 1)) - 1

    return (value * 0xFFFF / scale) >> 8
  }
}

export function set_depth(glyph, depth) {
  let pixels = []
  let fn = set_byte_depth(depth)

  for (let y = 0; y < glyph.bbox.height; y++) {
    pixels.push(glyph.pixels[y].map(fn))
  }

  return Object.assign({}, glyph, { pixels })
}

function count_bits(val) {
  let count = 0
  val = ~~val

  while (val) {
    count++
    val >>= 1
  }

  return count
}

// Minimal number of bits to store unsigned value
export const unsigned_bits = count_bits

// Minimal number of bits to store signed value
export function signed_bits(val) {
  if (val >= 0) return count_bits(val) + 1

  return count_bits(Math.abs(val) - 1) + 1
}

// Align value to 4x - useful to create word-aligned arrays
function align4(size) {
  if (size % 4 === 0) return size
  return size + 4 - (size % 4)
}

export { align4 }

// Align buffer length to 4x (returns copy with zero-filled tail)
export function balign4(buf) {
  const alignedLength = align4(buf.length)
  const alignedBuf = new Uint8Array(alignedLength)
  alignedBuf.set(new Uint8Array(buf))
  return alignedBuf.buffer
}

// Pre-filter image to improve compression ratio
// In this case - XOR lines, because it's very effective
// in decompressor and does not depend on bpp.
export function prefilter(pixels) {
  return pixels.map((line, l_idx, arr) => {
    if (l_idx === 0) return line.slice()

    return line.map((p, idx) => p ^ arr[l_idx - 1][idx])
  })
}

// Convert array with uint16 data to buffer
export function bFromA16(arr) {
  const buf = new ArrayBuffer(arr.length * 2)
  const view = new DataView(buf)

  for (let i = 0; i < arr.length; i++) {
    view.setUint16(i * 2, arr[i], true) // little endian
  }

  return buf
}

// Convert array with uint32 data to buffer
export function bFromA32(arr) {
  const buf = new ArrayBuffer(arr.length * 4)
  const view = new DataView(buf)

  for (let i = 0; i < arr.length; i++) {
    view.setUint32(i * 4, arr[i], true) // little endian
  }

  return buf
}

function chunk(arr, size) {
  const result = []
  for (let i = 0; i < arr.length; i += size) {
    result.push(arr.slice(i, i + size))
  }
  return result
}

// Dump long array to multiline format with X columns and Y indent
export function long_dump(arr, options = {}) {
  const defaults = {
    col: 8,
    indent: 4,
    hex: false
  }

  let opts = Object.assign({}, defaults, options)
  let indent = ' '.repeat(opts.indent)

  return chunk(Array.from(arr), opts.col)
    .map(l => l.map(v => (opts.hex ? `0x${v.toString(16)}` : v.toString())))
    .map(l => `${indent}${l.join(', ')}`)
    .join(',\n')
}

// stable sort by pick() result
export function sort_by(arr, pick) {
  return arr
    .map((el, idx) => ({ el, idx }))
    .sort((a, b) => (pick(a.el) - pick(b.el)) || (a.idx - b.idx))
    .map(({ el }) => el)
}

export function sum(arr) {
  return arr.reduce((a, v) => a + v, 0)
}

// 默认导出所有函数
const utils = {
  set_depth,
  unsigned_bits,
  signed_bits,
  align4,
  balign4,
  prefilter,
  bFromA16,
  bFromA32,
  long_dump,
  sort_by,
  sum
}

export default utils
