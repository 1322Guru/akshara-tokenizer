# benchmark_2026_07 eval corpus manifest

Source: FLORES-200 devtest (Meta NLLB official mirror).
Download URL: https://dl.fbaipublicfiles.com/nllb/flores200_dataset.tar.gz
Downloaded: 2026-07-13
Tarball sha256: b8b0b76783024b85797e5cc75064eb83fc5288b41e9654dabc7be6ae944011f6

Held-out rationale: FLORES-200 is a curated evaluation set held out from
training corpora. AksharaTokenizer v1's SentencePiece model was trained on
AI4Bharat Sangraha ("verified", splits hin/pan/tam). FLORES devtest is a
disjoint, independent source; no FLORES text was used to build the tokenizer.

How obtained: extracted flores200_dataset/devtest/<code>.devtest from the
tarball; each eval_<script>.txt is an exact, unmodified copy (full 1012-line
devtest, no sampling).

| script (SCRIPTS key) | FLORES code | language | lines | chars  | sha256 |
|----------------------|-------------|----------|-------|--------|--------|
| devanagari           | hin_Deva    | Hindi    | 1012  | 132091 | 5f5fd39acadca29fb044a0398e81869e48f37de979df086f2fad4a7d1fd2d015 |
| gurmukhi             | pan_Guru    | Punjabi  | 1012  | 134437 | 68f00ed7ef54ede7b757a5f10b25bf48d7f08e1f98080f44c7912a1428ee131f |
| tamil                | tam_Taml    | Tamil    | 1012  | 155145 | a18b26bf278e458f085c70173d6789d6108cb2e3346c81a1bd0f8aceb4ea30e4 |
| telugu               | tel_Telu    | Telugu   | 1012  | 133517 | 2dc641b4fb69347efe4b0c0f2063372c643f20c664b41a1f4421b69ba2a06420 |
| bengali              | ben_Beng    | Bengali  | 1012  | 130054 | 6699aa77b4c93d520971868cd5ff06a1e3b5ddfde852da13337f5194bc23086f |
| kannada              | kan_Knda    | Kannada  | 1012  | 139152 | 58e8ed5ef79cfd9994e7d4010d22b5ce72c3559f0c8e988fbde11fa58a720cd8 |
| english (info only)  | eng_Latn    | English  | 1012  | 132978 | 612e9fbe87997617c0fa8fa8929654a4f49b728d96738112c2b86ef6a1d78d88 |

All char counts are within the 50k-200k target. Every supported script has a file.
Provenance kept alongside: flores200_dataset.tar.gz and flores200_dataset/devtest/.
