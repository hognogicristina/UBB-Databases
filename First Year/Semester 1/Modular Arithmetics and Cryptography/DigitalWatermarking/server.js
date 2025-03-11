const express = require('express');
const multer = require('multer');
const sharp = require('sharp');
const path = require('path');

const app = express();
const upload = multer();

app.use(express.json({limit: '50mb'}));
app.use(express.urlencoded({limit: '50mb', extended: true}));
app.use(express.static(path.join(__dirname, 'client')));

async function applyInvisibleWatermark(imageBuffer, K, N) {
  const inputSharp = sharp(imageBuffer).ensureAlpha();
  const {data: rawData, info} = await inputSharp.raw().toBuffer({resolveWithObject: true});
  const {width, height, channels} = info;
  const originalM = rawData[0];

  for (let i = 0; i < rawData.length; i += 4) {
    rawData[i] = (rawData[i] + K) % N;
    rawData[i + 1] = (rawData[i + 1] + K) % N;
    rawData[i + 2] = (rawData[i + 2] + K) % N;
    rawData[i + 3] = 255;
  }

  const newW = rawData[0];
  const watermarkedBuffer = await sharp(rawData, {
    raw: {width, height, channels}
  }).png().toBuffer();
  const watermarkedNoCircleBase64 = watermarkedBuffer.toString('base64');

  const circleX = newW % width;
  const circleY = (newW + K) % height;
  const circleSvg = `
    <svg width="${width}" height="${height}">
      <circle 
        cx="${circleX}" 
        cy="${circleY}" 
        r="5" 
        stroke="red" 
        stroke-width="2" 
        fill="none" />
    </svg>
  `;
  const watermarkedWithCircle = await sharp(watermarkedBuffer)
    .composite([{input: Buffer.from(circleSvg), top: 0, left: 0}])
    .png()
    .toBuffer();
  const watermarkedWithCircleBase64 = watermarkedWithCircle.toString('base64');

  return {
    mValue: originalM,
    wValue: newW,
    watermarkedWithCircleBase64,
    watermarkedNoCircleBase64
  };
}

app.post('/watermark', upload.single('image'), async (req, res) => {
  try {
    const imageBuffer = req.file.buffer;
    const K = parseInt(req.body.key, 10) || 0;
    const N = parseInt(req.body.modulus, 10) || 256;

    const result = await applyInvisibleWatermark(imageBuffer, K, N);
    return res.json({
      mValue: result.mValue,
      wValue: result.wValue,
      imageBase64: result.watermarkedWithCircleBase64,
      imageBase64NoCircle: result.watermarkedNoCircleBase64
    });
  } catch (err) {
    console.error(err);
    return res.status(500).json({error: 'Failed to apply invisible watermark.'});
  }
});

app.post('/decode-watermark', upload.none(), async (req, res) => {
  try {
    const {imageBase64, key, modulus} = req.body;
    if (!imageBase64) {
      return res.status(400).json({error: 'No image data provided.'});
    }
    const K = parseInt(key, 10) || 0;
    const N = parseInt(modulus, 10) || 256;

    const watermarkedBuffer = Buffer.from(imageBase64, 'base64');

    const inputSharp = sharp(watermarkedBuffer).ensureAlpha();
    const {data: rawData, info} = await inputSharp.raw().toBuffer({resolveWithObject: true});
    const {width, height, channels} = info;

    for (let i = 0; i < rawData.length; i += 4) {
      rawData[i] = (rawData[i] - K + N) % N;
      rawData[i + 1] = (rawData[i + 1] - K + N) % N;
      rawData[i + 2] = (rawData[i + 2] - K + N) % N;
      rawData[i + 3] = 255;
    }

    const revertedBuffer = await sharp(rawData, {
      raw: {width, height, channels}
    }).png().toBuffer();

    return res.json({decodedBase64: revertedBuffer.toString('base64')});
  } catch (error) {
    console.error(error);
    return res.status(500).json({error: 'Failed to decode invisible watermark.'});
  }
});

function escapeXml(str = '') {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');
}

async function applyVisibleWatermark(mainBuffer, watermarkBuffer, options = {}) {
  const {left = 0, top = 0, width = 0, height = 0} = options;

  const main = sharp(mainBuffer).ensureAlpha();
  const mainMeta = await main.metadata();

  let wm = sharp(watermarkBuffer).ensureAlpha();
  let wmMeta = await wm.metadata();

  let finalWmBuffer = watermarkBuffer;
  if (width > 0 || height > 0) {
    wm = wm.resize({
      width: width > 0 ? width : undefined,
      height: height > 0 ? height : undefined,
      fit: 'inside'
    });
    finalWmBuffer = await wm.png().toBuffer();
    wmMeta = await sharp(finalWmBuffer).metadata();
  }

  const willExceedWidth = left + wmMeta.width > mainMeta.width;
  const willExceedHeight = top + wmMeta.height > mainMeta.height;

  if (willExceedWidth || willExceedHeight) {
    const maxWidth = Math.max(1, mainMeta.width - left);
    const maxHeight = Math.max(1, mainMeta.height - top);
    finalWmBuffer = await sharp(finalWmBuffer)
      .resize({
        width: Math.min(wmMeta.width, maxWidth),
        height: Math.min(wmMeta.height, maxHeight),
        fit: 'inside'
      })
      .png()
      .toBuffer();
  }

  return await main
    .composite([
      {
        input: finalWmBuffer,
        left,
        top,
        blend: 'over'
      }
    ])
    .png()
    .toBuffer();
}

function createTextWatermarkSvg(text, w, h, color = '#000', fontSize = 24, fontFamily = 'Arial') {
  const escapedText = escapeXml(text);
  return Buffer.from(`
    <svg width="${w}" height="${h}" xmlns="http://www.w3.org/2000/svg">
      <rect width="100%" height="100%" fill="none" />
      <text 
        x="50%" 
        y="50%" 
        fill="${color}"
        font-size="${fontSize}"
        font-family="${fontFamily}"
        dominant-baseline="middle"
        text-anchor="middle">
        ${escapedText}
      </text>
    </svg>
  `);
}

app.post('/encode-visible', upload.fields([
  {name: 'image', maxCount: 1},
  {name: 'watermark', maxCount: 1}
]), async (req, res) => {
  try {
    const text = req.body.text || '';

    const mainUpload = req.files['image'] && req.files['image'][0];
    const wmUpload = req.files['watermark'] && req.files['watermark'][0];
    if (!mainUpload) {
      return res.status(400).json({error: 'Please provide a main image.'});
    }

    const left = parseInt(req.body.left, 10) || 0;
    const top = parseInt(req.body.top, 10) || 0;
    const wWidth = parseInt(req.body.wmWidth, 10) || 0;
    const wHeight = parseInt(req.body.wmHeight, 10) || 0;

    let watermarkBuffer;
    if (text) {
      const boxW = wWidth > 0 ? wWidth : 300;
      const boxH = wHeight > 0 ? wHeight : 100;
      watermarkBuffer = createTextWatermarkSvg(text, boxW, boxH, '#000', 24, 'Arial');
    } else if (wmUpload) {
      watermarkBuffer = wmUpload.buffer;
    } else {
      return res.status(400).json({error: 'Provide either a watermark image or text.'});
    }

    const watermarkedBuffer = await applyVisibleWatermark(
      mainUpload.buffer,
      watermarkBuffer,
      {left, top, width: wWidth, height: wHeight}
    );

    const base64 = watermarkedBuffer.toString('base64');
    return res.json({watermarked: base64});
  } catch (err) {
    console.error(err);
    return res.status(500).json({error: 'Failed to apply visible watermark.'});
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server listening at http://localhost:${PORT}`);
});