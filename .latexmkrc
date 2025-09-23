$pdf_mode = 5;

$pdflatex = 'pdflatex -interaction=nonstopmode -file-line-error -synctex=1 %O %S';
$xelatex  = 'xelatex  -interaction=nonstopmode -file-line-error -synctex=1 %O %S';
$lualatex = 'lualatex -interaction=nonstopmode -file-line-error -synctex=1 %O %S';

$aux_dir = 'build/aux';
$out2_dir  = 'build/dist';
