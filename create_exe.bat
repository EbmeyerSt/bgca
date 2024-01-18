pyinstaller --name bgca --onedir --icon=icon.ico ^
 --add-data="default_layouts.txt;." ^
 --hidden-import=openpyxl.cell._writer ^
 --hidden-import=sklearn.metrics ^
 --hidden-import=sklearn.metrics._pairwise_distances_reduction._datasets_pair ^
 --hidden-import=sklearn.metrics._pairwise_distances_reduction._middle_term_computer ^
  main.py 
