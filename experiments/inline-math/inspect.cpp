#include <allheaders.h>
#include <tesseract/baseapi.h>
#include <tesseract/resultiterator.h>

#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <memory>
#include <string>

int main(int argc, char **argv) {
    if (argc < 2) return 1;
    const char *language = "eng";
    int choice_mode = 2;
    for (int i = 2; i < argc; ++i) {
        const std::string option(argv[i]);
        if (option.rfind("--lang=", 0) == 0) language = argv[i] + 7;
        if (option == "--best-only") choice_mode = 0;
    }
    tesseract::TessBaseAPI api;
    if (api.Init(std::getenv("TESSDATA_PREFIX"), language, tesseract::OEM_LSTM_ONLY)) return 2;
    if (!api.SetVariable("lstm_choice_mode", choice_mode ? "2" : "0")) return 3;
    auto layout = tesseract::PSM_SINGLE_LINE;
    for (int i = 2; i < argc; ++i) {
        const std::string option(argv[i]);
        if (option == "--subscripts") {
            if (!api.SetVariable("lstm_detect_subscripts", "1")) return 3;
        } else if (option == "--recover") {
            if (!api.SetVariable("lstm_recover_subscripts", "1")) return 3;
        } else if (option == "--reread") {
            if (!api.SetVariable("lstm_reread_subscripts", "1")) return 3;
        } else if (option == "--best-only" || option.rfind("--lang=", 0) == 0) {
            continue;
        } else if (option == "--auto") {
            layout = tesseract::PSM_AUTO;
        } else if (option == "--block") {
            layout = tesseract::PSM_SINGLE_BLOCK;
        } else {
            return 1;
        }
    }
    api.SetPageSegMode(layout);
    Pix *image = pixRead(argv[1]);
    if (!image) return 4;
    api.SetImage(image);
    pixDestroy(&image);
    api.SetSourceResolution(300);
    if (api.Recognize(nullptr)) return 5;
    std::unique_ptr<tesseract::ResultIterator> it(api.GetIterator());
    if (!it) return 0;
    constexpr auto level = tesseract::RIL_SYMBOL;
    do {
        if (it->Empty(level)) continue;
        std::unique_ptr<char[]> symbol(it->GetUTF8Text(level));
        std::unique_ptr<char[]> word(it->GetUTF8Text(tesseract::RIL_WORD));
        int l, t, r, b;
        if (!symbol || !it->BoundingBox(level, &l, &t, &r, &b)) return 6;
        std::cout << std::quoted(symbol.get()) << ' ' << l << ' ' << t << ' '
                  << r << ' ' << b << ' ' << it->SymbolIsSubscript() << ' '
                  << it->SymbolIsSuperscript() << ' ' << std::quoted(word ? word.get() : "");
        if (!choice_mode) { std::cout << '\n'; continue; }
        tesseract::ChoiceIterator choice(*it);
        do {
            if (const char *text = choice.GetUTF8Text())
                std::cout << ' ' << std::quoted(text) << ' ' << choice.Confidence();
        } while (choice.Next());
        std::cout << '\n';
    } while (it->Next(level));
}
