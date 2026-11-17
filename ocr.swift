import Foundation
import Vision
import AppKit
let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.recognitionLanguages = ["zh-Hans", "en-US"]
request.usesLanguageCorrection = false
do {
    try VNImageRequestHandler(url: URL(fileURLWithPath: CommandLine.arguments[1])).perform([request])
    let rows = (request.results ?? []).compactMap { item -> [String:Any]? in
        guard let t = item.topCandidates(1).first else {return nil}
        let b = item.boundingBox
        return ["t":t.string, "x":b.minX,"y":1-b.maxY,"h":b.height]
    }
    FileHandle.standardOutput.write(try JSONSerialization.data(withJSONObject:rows))
} catch {
    fputs("图片文字识别失败，请重试或手动录入。", stderr)
    exit(1)
}
