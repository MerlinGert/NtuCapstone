import { describe, expect, test } from 'bun:test'

import { normalizeImportPayload } from './sessionIO.js'

describe('normalizeImportPayload', () => {
  test('preserves test-only patch marker and restores json image map references', () => {
    const imageDataUrl = 'data:image/png;base64,iVBORw0KGgo='
    const payload = normalizeImportPayload(
      {
        exportVersion: '1.0',
        isPatchTraceOnlyForTesting: true,
        coin: 'ACT',
        includesSnapshots: true,
        annotationSeqId: 9,
        userActionSequence: [
          {
            actionType: 'click_manipulation_card',
            sourceSnapshot: [
              {
                viewName: 'kline_chart',
                imagePath: 'images/action-0015-source-kline_chart-01.png',
              },
            ],
          },
        ],
        annotationRecords: [
          {
            id: 8,
            sourceView: 'behavior_details',
            sketchImagePath: 'images/annotation-0008-behavior_details.png',
          },
        ],
      },
      {
        'images/action-0015-source-kline_chart-01.png': imageDataUrl,
        'images/annotation-0008-behavior_details.png': imageDataUrl,
      },
    )

    expect(payload.isPatchTraceOnlyForTesting).toBe(true)
    expect(payload.annotationSeqId).toBe(9)
    expect(payload.userActionSequence[0].sourceSnapshot[0].dataUrl).toBe(imageDataUrl)
    expect(payload.userActionSequence[0].sourceSnapshot[0].imagePath).toBeUndefined()
    expect(payload.annotationRecords[0].sketchDataUrl).toBe(imageDataUrl)
    expect(payload.annotationRecords[0].sketchImagePath).toBeUndefined()
  })

  test('defaults test-only patch marker to false for normal imports', () => {
    const payload = normalizeImportPayload({
      exportVersion: '1.0',
      userActionSequence: [],
      annotationRecords: [],
    })

    expect(payload.isPatchTraceOnlyForTesting).toBe(false)
  })
})
