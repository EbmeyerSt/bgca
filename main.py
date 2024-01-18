import os
import io
import sys
import json
import openpyxl
import xlsxwriter
import openpyxl.cell._writer
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
from sklearn.metrics import *
from pygam import LinearGAM, s
from PyQt5.QtCore import *
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import *

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

#https://stackoverflow.com/questions/31836104/pyinstaller-and-onefile-how-to-include-an-image-in-the-exe-file
def resource_path(relative_path):
    """ Get absolute path to resource (e.g files), works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


#Create QMainWindow subclass in order to customize main window
class MainWindow(QMainWindow):
    """Initializes main window and associated widgets"""

    def __init__(self):
        super(MainWindow, self).__init__()

        self.setWindowTitle('Growthcurve analyzer')
        layout=QGridLayout()

        n='\n' #linebreak for f-strings
        
        #Define input widgets
        spacer_widget=QLabel(' ')

        #Input widgets for averaging, replicates, backgrounds, number of used columns and positive controls
        reprow_label=QLabel('Replicates')
        reprow_label.setToolTip(f"Specify which rows are replicates of each other.{n}E.g. 'A:B:C, D:E' means that rows A, B and C are{n}replicates and row D and E are replicates. If wells in {n}the same row are replicates of each other, supply these as{n} e.g. A01:A02:A03, ...If there are no replicates on the plate, leave this field empty.")
        self.rep_rows=QLineEdit()

        bgrow_label=QLabel('Background rows')
        bgrow_label.setToolTip(f'Specify which rows provide background samples for{n}other rows. E.g "AB:CD, EF:GH" means that rows C{n}and D provide background for A and B and{n}rows G and H provide background to E and F. If there are{n}no background samples on the plate, leave this field empty.")')
        self.bg_rows=QLineEdit()

        avgrow_label=QLabel('Average replicates') #Make checkbox
        avgrow_label.setToolTip('Check to average replicate rows.')
        self.avg_rows=QCheckBox()

        #Add Checkbox for using smoothened curves or not
        smooth_label=QLabel('Smoothen curves')
        smooth_label.setToolTip(f'If checked, a generalized additive model will be fitted to each curve and{n}calculations will be performed on smoothened curve.')
        self.smoothen_curves=QCheckBox()

        numcols_label=QLabel('Plate columns used')
        numcols_label.setToolTip('Number of plate columns used plate layout.')
        self.num_cols=QComboBox()
        self.num_cols.addItems([str(i) for i in range(1, 13)])

        pos_label=QLabel('Positive controls') #Such as A11:B11, A12:B12 (think about replicates here)
        pos_label.setToolTip(f'Specify which wells provide positive controls. If well A11 and A12 are{n}positive controls for row A, provide as A11+A12:A. For several rows:{n}A11+A12:A, B11+B12:B, ...')#TODO: This needs to be specified more
        self.pos_contr=QLineEdit()

        #Define button for plotting
        self.plot_button=QPushButton('Plot growth curves')
        self.plot_button.setEnabled(False)

        #Input widgets for lag calculation method
        lag_calc_label=QLabel('Lag-time calculation')
        lag_calc_label.setToolTip('Choose how to calculate the timepoint of lag-phase end, must be float or integer')
        self.lag_calc=QComboBox()
        self.lag_calc.addItems(['OD value', '% max. OD'])
        self.lag_calc.model().item(1).setEnabled(False)

        self.lag_calc_input_label=QLabel(f'{self.lag_calc.currentText()}')
        self.lag_calc_input_label.setToolTip('Enter threshold value')
        self.lag_calc_input=QLineEdit()

        #Add drop down lists for default plate layouts and Lowec calculation
        layout_label=QLabel('Plate Layout')
        layout_label.setToolTip('Choose between default or custom plate layouts.')
        #Read layouts from file
        self.layout_defaults=QComboBox()
        self.layout_defaults.addItems([k for k, v in json.load(open(resource_path('default_layouts.txt'),'r')).items()])

        lowec_label=QLabel('Loec calculation')
        lowec_label.setToolTip('Specify if and how LOEC calculation should be done.')
        self.lowec_calc=QComboBox()
        self.lowec_calc.addItems(['None', 'ANOVA lag', 'ANOVA AUC','ANOVA yield', '% PC lag', '% PC AUC', '% PC yield'])

        lowec_input_label=QLabel('Threshold value')
        lowec_input_label.setToolTip('Loec threshold value, must be float or integer')
        self.lowec_input=QLineEdit()
        self.lowec_input.setEnabled(False) #Have input to this disabled if not '% PC lag' or '% PC AUC' are chosen

        #Add widget to define concentrations
        conc_label=QLabel('Concentrations (optional)')
        conc_label.setToolTip(f'Concentrations used in plate columns, starting at column 0. Can be list of strings{n} (e.g 1mg/ml, 0.75mg/ml, ...) or highest concentration followed by dilution,{n}e.g 12mg/ml:4 for four fold dilutions starting with 12 mg/ml.')
        self.concentrations=QLineEdit()
        unit_label=QLabel('Unit')
        unit_label.setToolTip('e.g mg/l, ug/l')
        self.concentration_unit=QLineEdit()

        #add widget for MIC value calculation
        mic_label=QLabel('MIC calculation')
        self.mic_calc=QComboBox()
        self.mic_calc.addItems(['None', 'max. OD'])

        mic_input_label=QLabel('Threshold value')
        self.mic_input=QLineEdit()
        self.mic_input.setEnabled(False)

        #Defaultlayout button to save/remove layouts
        platelayout_label=QLabel('Add/Remove Layout')
        self.addbutton=QPushButton('Add')
        self.addbutton.setFixedSize(QSize(55, 23))
        self.rmbutton=QPushButton('Remove')
        self.rmbutton.setFixedSize(QSize(55, 23))
        self.rmbutton.setEnabled(False)
        self.addbutton.setToolTip('Add a custom default plate layout.')
        self.addbutton.resize(70, 50)
        self.rmbutton.setToolTip('Remove a default plate layout')

        #Push button to call BrowseFiles class and open browse file window
        filebuttonlabel=QLabel('Input file:') #make file browser
        filebuttonlabel.setToolTip('Choose input file - must be .xlsx or .csv format')
        self.filebutton=QPushButton('Browse files')
        #Add Qlabel to display input file path
        self.filelabel=QLineEdit() #When a file is selected, change text here

        #Submitbutton, starts calculations when pressed and enables plot button
        submittbutton_label=QLabel('')
        submittbutton_label.setToolTip('Submit parameters and run calculations')
        self.submitbutton=QPushButton('Submit')

        #Set output dataframes as attributes to make them accessible for plotting
        self.metrics=None
        self.df=None
        self.gams=None
        self.shifted_gams=None
        self.df_raw=None
        self.lowecs=None
        self.noecs=None
        self.mic=None
        self.conc_dict=None
        self.std_dict=None
        self.std_calculated=False
        self.reps_in_rows=False
        self.reps_in_cols=False

        #Place widgets in grid
        layout.addWidget(filebuttonlabel, 0, 0, 1, 2, alignment=Qt.AlignBottom)
        layout.addWidget(self.filelabel, 1, 0, 1, 2, alignment=Qt.AlignBottom)
        layout.addWidget(self.filebutton, 2, 0, 1, 2)
        layout.addWidget(spacer_widget, 3, 0, 1, 2)
        layout.addWidget(layout_label, 4, 0, alignment=Qt.AlignBottom)
        layout.addWidget(self.layout_defaults, 5, 0)
        layout.addWidget(platelayout_label, 4, 1, alignment=Qt.AlignBottom)
        layout.addWidget(self.addbutton, 5, 1, alignment=Qt.AlignLeft)
        layout.addWidget(self.rmbutton, 5, 1, alignment=Qt.AlignRight)
        layout.addWidget(spacer_widget, 6, 0, 1, 2)
        layout.addWidget(reprow_label, 7,0, alignment=Qt.AlignBottom)
        layout.addWidget(self.rep_rows, 8, 0)
        layout.addWidget(bgrow_label, 7,1, alignment=Qt.AlignBottom)
        layout.addWidget(self.bg_rows, 8, 1)
        layout.addWidget(numcols_label, 9,0, alignment=Qt.AlignBottom)
        layout.addWidget(self.num_cols, 10, 0)
        layout.addWidget(avgrow_label, 9, 1, alignment=Qt.AlignBottom)
        layout.addWidget(self.avg_rows, 10, 1)
        layout.addWidget(pos_label, 11, 0, alignment=Qt.AlignBottom)
        layout.addWidget(self.pos_contr, 12, 0)
        layout.addWidget(smooth_label, 11, 1, alignment=Qt.AlignBottom)
        layout.addWidget(self.smoothen_curves, 12, 1)
        layout.addWidget(conc_label, 13, 0, alignment=Qt.AlignBottom)
        layout.addWidget(self.concentrations, 14, 0)
        layout.addWidget(unit_label, 13, 1, alignment=Qt.AlignBottom)
        layout.addWidget(self.concentration_unit, 14, 1)
        layout.addWidget(spacer_widget, 15, 0, 1, 2)
        layout.addWidget(lag_calc_label, 16, 0, alignment=Qt.AlignBottom)
        layout.addWidget(self.lag_calc, 17, 0)
        layout.addWidget(self.lag_calc_input_label, 16, 1, alignment=Qt.AlignBottom)
        layout.addWidget(self.lag_calc_input, 17, 1)
        layout.addWidget(lowec_label, 18, 0, alignment=Qt.AlignBottom)
        layout.addWidget(self.lowec_calc, 19, 0)
        layout.addWidget(lowec_input_label, 18, 1, alignment=Qt.AlignBottom)
        layout.addWidget(self.lowec_input, 19, 1)
        layout.addWidget(mic_label, 20, 0, alignment=Qt.AlignBottom)
        layout.addWidget(self.mic_calc, 21, 0)
        layout.addWidget(mic_input_label, 20, 1, alignment=Qt.AlignBottom)
        layout.addWidget(self.mic_input, 21, 1)
        layout.addWidget(spacer_widget, 22, 0, 1, 2)
        layout.addWidget(submittbutton_label, 23, 0, 1, 2, alignment=Qt.AlignCenter)
        layout.addWidget(self.submitbutton, 24, 0, 1, 2, alignment=Qt.AlignCenter)
        layout.addWidget(spacer_widget, 25, 0, 1, 2)
        layout.addWidget(spacer_widget, 26, 0, 1, 2)
        layout.addWidget(self.plot_button, 27, 0, 1, 2)

        #set height of rows containing labels and spacing between grid cells
        l_rows=[1, 4, 7, 9, 11, 13, 16, 18, 20]
        for r in l_rows:
            layout.setRowMinimumHeight(r, 25)

        layout.setVerticalSpacing(1)
        
        #Perform Widget operations
        #When filebutton is clicked call filebuttonclicked()
        self.filebutton.clicked.connect(self.filebuttonclicked)

        #When value in default_layouts is changed, call set_defaults()
        self.layout_defaults.currentTextChanged.connect(self.set_defaults)

        self.pos_contr.textChanged.connect(self.enableperclag)

        #When value in lowec_input is changed, call enable_lowec_input
        self.lowec_calc.currentTextChanged.connect(self.enable_lowec_input)

        #When value for MIC calculation is changed, call enable_mic_input
        self.mic_calc.currentTextChanged.connect(self.enable_mic_input)

        #When value in lag_calc is changed, change input label accordingly
        self.lag_calc.currentTextChanged.connect(self.change_laglabel)

        #When add layout button is clicked, open the respective window
        self.addbutton.clicked.connect(self.addbuttonclicked)

        #When removebutto n is clicked, open th erespective window
        self.rmbutton.clicked.connect(self.rmbuttonclicked)

        #When submitbutton is clicked, call submitbuttonclicked()
        self.submitbutton.clicked.connect(self.submitbuttonclicked)

        #When plotbutton is clicked, open plotting window
        self.plot_button.clicked.connect(self.plotbuttonclicked)

        widget=QWidget()
        widget.setLayout(layout)

        #Set central widget of window
        self.setCentralWidget(widget)

    def enableperclag(self):
        """Enable/Disable % max. OD option for lag calculation with changing positive control inputs"""

        if self.pos_contr.text()=='':
                self.lag_calc.model().item(1).setEnabled(False)
        else:
            self.lag_calc.model().item(1).setEnabled(True)

    def enable_mic_input(self):
        """ Enable input for MIC threshold value """

        if self.mic_calc.currentText()!='None':
            self.mic_input.setEnabled(True)
        else:
            self.mic_input.setEnabled(False)

    def change_laglabel(self):
        """Change label for lag calculation input box on selection of alternative"""

        self.lag_calc_input_label.setText(self.lag_calc.currentText())

    def enable_lowec_input(self):
        """Enable input for loec calculation widget and uncheck averaging rows in case ANOVA is chosen"""

        if self.lowec_calc.currentText()=='% PC lag' or self.lowec_calc.currentText()=='% PC AUC' \
        or self.lowec_calc.currentText()=='% PC yield':
            self.lowec_input.setEnabled(True)
        else:
            self.lowec_input.setEnabled(False)
            self.lowec_input.setText('')
        
        if 'ANOVA' in self.lowec_calc.currentText():
            self.avg_rows.setChecked(False)

    def rmbuttonclicked(self):
        """ Open layout removal window"""

        self.w=RemoveLayoutWindow(self)
        self.w.show()

    def addbuttonclicked(self):
        """ Open layout saving window """

        self.w=AddLayoutWindow(self)
        self.w.show()

    def plotbuttonclicked(self):
        """Open plotting window"""

        self.plot_button.setEnabled(False)
        self.w=PlotWindow(self)
        self.w.show()

    def match_concentrations(self):
        """Match user provided concentrations with plate column numbers"""

        if self.pos_contr.text()!='':
            #Assumes positive controls to be at end or beginning of row, same layout for all rows
            pos=self.pos_contr.text().split(',')
            #Get positive control positions
            if len(pos)>1 and not '+' in pos[0]:
                pos_cols={x.split(':')[0][-2:] for x in pos}
            elif len(pos)>1 and '+' in pos[0]:
                pos_cols={y.strip()[-2:] for x in pos for y in x.strip().split(',')[0].split(':')[0].split('+')}
            elif len(pos)==1 and '+' in pos[0]:
                pos_cols={y.strip()[-2:] for x in pos for y in x.strip().split(':')[0].split('+')}
            elif len(pos)==1 and not '+' in pos[0]:
                pos_cols={x.split(':')[0] for x in pos}

            conc_cols=int(self.num_cols.currentText())-len(pos_cols)

            #match concentration list to plate column number based on where positive controls are located
            #Again, this assumes that all positive controls are located either at the beginning or the end of a row
            if any(x in [float(x) for x in list(pos_cols)] for x in [*range(1,5)]):
                pos_end=max([int(x) for x in list(pos_cols)])
                cols=['0'+str(i) if len(str(i))<2 else str(i) for i in range(pos_end, conc_cols+1)]
            else:
                pos_end=min(list([int(x) for x in list(pos_cols)]))
                cols=['0'+str(i) if len(str(i))<2 else str(i) for i in range(1, pos_end+1)]

        else:
            cols=['0'+str(i) if len(str(i))<2 else str(i) for i in range(1, int(self.num_cols.currentText())+1)]   
            
        if ',' in self.concentrations.text():
            conc_dict={x[0].strip():str(x[1].strip())+self.concentration_unit.text() for x in zip(cols, self.concentrations.text().split(','))}

        elif ':' in self.concentrations.text():
            high_conc=float(self.concentrations.text().split(':')[0].strip())
            dilution_factor=float(self.concentrations.text().split(':')[1].strip())
                
            conc_dict={}
            current_conc=high_conc
            for i, c in enumerate(cols):
                if i>0:
                    current_conc/=dilution_factor
                    conc_dict[c]=str(round(current_conc,6))+self.concentration_unit.text()
                else:
                    conc_dict[c]=str(round(current_conc,6))+self.concentration_unit.text()

        return conc_dict

    def set_defaults(self):
        """Change values in the form according to default layouts"""

        #Load defaults file as dictionary
        layouts=json.load(open(resource_path('default_layouts.txt'), 'r'))
        default=self.layout_defaults.currentText()

        if default=='Custom':
            pass #Do nothing and let user fill form

        else:
            #Set values in form according to declans and Deos Biocide setup
            self.rep_rows.setText(layouts[default]['reps'])
            self.bg_rows.setText(layouts[default]['bg'])

            if layouts[default]['avg']==1:
                self.avg_rows.setChecked(True)
            else:
                self.avg_rows.setChecked(False)

            if layouts[default]['smoothen']==1:
                self.smoothen_curves.setChecked(True)
            else:
                self.smoothen_curves.setChecked(False)

            self.num_cols.setCurrentText(layouts[default]['col_num'])
            self.pos_contr.setText(layouts[default]['pos'])
            self.lowec_calc.setCurrentText(layouts[default]['lowec_calc'])
            self.lowec_input.setText(layouts[default]['lowec_calc_input'])
            self.lag_calc.setCurrentText(layouts[default]['lag_calc'])
            self.lag_calc_input.setText(layouts[default]['lag_calc_input'])
            self.mic_calc.setCurrentText(layouts[default]['mic_calc'])
            self.mic_input.setText(layouts[default]['mic_calc_input'])
            self.concentrations.setText(layouts[default]['conc'])
            self.concentration_unit.setText(layouts[default]['conc_unit'])

        #Talk to Joakim about more layouts
        if self.layout_defaults.currentText()!='Custom':

            self.rmbutton.setEnabled(True)
            self.rep_rows.setEnabled(False)
            self.avg_rows.setEnabled(False)
            self.bg_rows.setEnabled(False)
            self.smoothen_curves.setEnabled(False)
            self.pos_contr.setEnabled(False)
            self.num_cols.setEnabled(False)
            self.lag_calc_input.setEnabled(False)
            self.mic_input.setEnabled(False)
        else:
            self.rmbutton.setEnabled(False)
            self.rep_rows.setEnabled(True)
            self.avg_rows.setEnabled(True)
            self.bg_rows.setEnabled(True)
            self.smoothen_curves.setEnabled(True)
            self.pos_contr.setEnabled(True)
            self.num_cols.setEnabled(True)
            self.lag_calc_input.setEnabled(True)
            self.mic_input.setEnabled(True)

    def submitbuttonclicked(self):
        """Collect info from all widgets after submitbutton has been clicked"""

        filename=self.filelabel.text()
        lowec=self.lowec_calc.currentText()
        default_l=self.layout_defaults.currentText()
        reps=self.rep_rows.text()
        bg=self.bg_rows.text()
        avg=self.avg_rows.isChecked()
        num_c=int(self.num_cols.currentText())
        pos=self.pos_contr.text()
        smoothen=self.smoothen_curves.isChecked()

        for p in [pos, lowec, default_l, reps, bg, avg, num_c]:
            print(str(p))

        #Check integrity of input
        if default_l=='Custom':
            chk=self.check_input_integrity()
            if len(chk)>0:
                #print error message
                self.pop_errormsg(chk)
                return
            
        else:
            """If default layout is not custom, we assume that the values entered
            into the form are correct, since they are automatically entered.
            Only check that file is speciefied correctly"""
            errors=[]
            if os.path.isfile(os.path.normpath(filename)):
                pass

            else:
                errors.append(f'Invalid filename. Use the browsing option to select the input file.')
                #print error message
                self.pop_errormsg(errors)
                return
            
        self.plot_button.setEnabled(True)
        #self.plot_button.setStyleSheet('background-color: greenyellow')
        #Calculate metrics
        self.metrics, self.df, self.gams, self.shifted_gams, self.df_raw, self.lowecs, self.noecs, self.mics, self.conc_dict, self.std_dict = self.growth_metrics()
    
    def pop_errormsg(self, errorlist):
        """Make a little error window pop up"""

        errormsg=QMessageBox()
        errormsg.setIcon(QMessageBox.Critical)
        errormsg.setText(f'{errorlist[0]}')
        errormsg.setWindowTitle('Error')
        errormsg.exec_()

    def filebuttonclicked(self):
        """Opens an instance of BrowseFiles class once the browse files button is clicked,
        opening a QFileDialog window to select the file from"""
        print('Clicked!')
        wig=BrowseFiles()
        wig.show()
        self.filelabel.setText(f'{wig.filename[0]}')
    
    def growth_metrics(self):
        """Wrapper function for processing xlsx omnilog input and calculating growth curve metrics"""
        #Read in dataframe
        
        if self.filelabel.text().endswith('.xlsx'):
            df=pd.read_excel(resource_path(self.filelabel.text()), header=10)
        elif self.filelabel.text().endswith('.csv'):
            df=pd.read_csv(resource_path(self.filelabel.text()))

        #Rename column headers to exclude whitespaces
        df.rename({c:c.strip() for c in df.columns}, axis=1, inplace=True)
        df_raw=df.copy(deep=True)

        #Calculate variance between replicates if replicates are provided
        if self.rep_rows.text()!='':
            std_dict=self.get_replicate_variance(df_raw)
        else:
            std_dict=None

        if self.avg_rows.isChecked()==True and self.rep_rows.text()!='':
            df=self.average_replicates(df, self.rep_rows.text())
        if self.bg_rows.text()!='':
            df=self.substract_background(df, self.bg_rows.text(), self.avg_rows.isChecked())

        if self.smoothen_curves.isChecked()==True:
            df=self.set_to_zero(df)
            gams=self.fit_gam_to_avg(df)
            shifted_gams=self.shift_curves(gams)
            metrics=self.calculate_metrics(shifted_gams)
        else:
            metrics=self.calculate_metrics(df)
            gams=''
            shifted_gams=''

        if self.lowec_calc.currentText()!='None':
            lowecs, noecs=self.calculate_lowec(metrics)
        else:
            lowecs=None
            noecs=None

        if self.mic_calc.currentText()!='None':
            mics=self.calculate_mic(metrics)
        else:
            mics=None

        if self.concentrations.text()!='':
            conc_dict=self.match_concentrations()
        else:
            conc_dict=None

        return metrics, df, gams, shifted_gams, df_raw, lowecs, noecs, mics, conc_dict, std_dict

    def check_input_integrity(self):
        """Takes user input from all widgets and checks integrity.
        If input is not correct, and error is returned."""

        filename=self.filelabel.text()
        reps=self.rep_rows.text()
        bg=self.bg_rows.text()
        pos=self.pos_contr.text()

        errors=[]
        rownames=['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
        nl='\n'

        #Check file
        if os.path.isfile(os.path.normpath(filename)):
            pass
        else:
            errors.append(f'Invalid filename. Use the browsing option{nl}to select the input file.')
        
        #Check replicate row format
        if reps!='':
            #Check if replicates are supplied by row or by column
            reps_in_rows, reps_in_cols=self.determine_replicate_setup(reps)

            if reps_in_rows==True and reps_in_cols==False:
                #Check if row separator is correct
                if ':' in reps:
                    #Check if different replicate pairs are separated correctly
                    if ',' in reps:
                        #Check that none of the lists after , is empty
                        lens=[True if len(x.strip())>0 else False for x in reps.split(',')]
                        if lens==False:
                            errors.append(f'Invalid replicate entry:{nl}Entry missing after ",".')
                        #Check that only one row is defined per ':' separator
                        x=[len(x.strip()) for y in reps.split(',') for x in y.split(':')]
                        if np.mean(x)!=1:
                            errors.append(f'Invalid replicate entry:{nl}Only one rowname before ":" allowed')
                    else:
                        x=[len(x.strip()) for x in reps.split(':')]
                        if np.mean(x)!=1:
                            errors.append(f'Invalid replicate entry:{nl}Only one rowname before ":" allowed')

                else:
                    errors.append(f'Invalid replicate row separator:{nl}Enter rows that are replicates separated{nl}by ":".')

            elif reps_in_rows==False and reps_in_cols==True:
                #TODO: Build in check for this format here
                pass
        else:
            pass

        #Check background row format
        if bg!='':
            bgs=[]
            samps=[]
            #Check if row separator is correct
            if ':' in bg:
                #Check if different replicate pairs are separated correctly
                if ',' in bg:
                    #Check that none of the lists after , is empty #TODO: THIS IS NOT WORKING; CORRECT
                    lens=[True if len(x.strip())>0 else False for x in bg.split(',')]
                    if lens==False:
                        errors.append(f'Invalid background entry:{nl}Entry missing after ",".')
                    
                    for e in bg.split(','):
                        #Check that all values are valid row names and backgrounds
                        #Samples do not overlap
                        bgs.extend([x for x in e.strip().split(':')[1]])
                        samps.extend([x for x in e.strip().split(':')[0]])

                    if any(x.strip() in samps for x in bgs):
                        errors.append(f'Invalid background entry:{nl}Background and sample rows overlap!')
                        
                else:
                    
                    #Check that all values are valid row names and backgrounds
                    #Samples do not overlap
                    bgs.extend([x for x in bg.strip().split(':')[1]])
                    samps.extend([x for x in bg.strip().split(':')[0]])

                    if any(x.strip() in samps for x in bgs):
                        errors.append(f'Invalid background entry:{nl}Background and sample rows overlap!')
            else:
                errors.append(f'Invalid background row separator:{nl}Enter rows that are replicates separated{nl}by ":".')
        else:
            pass

        #Check positive control well format (format should be eg: A11+A12:A)
        #Meaning that well A11 and A12 provide positive controls for row A
        if pos!='':
            #Check if row separator is correct
            if ':' in pos:
                #Check if different replicate pairs are separated correctly
                if ',' in pos:
                    #Check that none of the lists after , is empty
                    lens=[True if len(x.strip())>0 else False for x in pos.split(',')]
                    if lens==False:
                        errors.append(f'Invalid positive control entry. Provide positive control positions as e.g {nl}A11+A12:A, B11+B12:B, ...')

                    if not '+' in pos:
                        #Check that all elements are correctly entered
                        well_corr=[]
                        row_corr=[]
                        for e in pos.split(','):
                            e=e.strip()
                            if not e.split(':')[0].strip()[0] in rownames:
                                errors.append(f'Invalid positive control row name. Provide positive control positions as e.g {nl}A11+A12:A, B11+B12:B, ...')
                            if int(e.split(':')[0].strip()[1:])>12:
                                errors.append(f'Invalid positive control column number.Provide positive control positions as e.g {nl}A11+A12:A, B11+B12:B, ...')
                                
                    else:
                        #Check that all elements are correctly entered
                        well_corr=[]
                        row_corr=[]
                        for e in pos.split(','):
                            e2=e.split(':')[0].strip()
                            for e3 in e2.split('+'):
                                if not e3[0] in rownames:
                                    errors.append(f'Invalid positive control row name. Provide positive control positions as e.g {nl}A11+A12:A, B11+B12:B, ...')
                                if int(e3[1:])>12:
                                    errors.append(f'Invalid positive control column number. Provide positive control positions as e.g {nl}A11+A12:A, B11+B12:B, ...')
                        
                else:
                    
                    if not bg.strip().split(':')[0][0] in rownames:
                        errors.append(f'Invalid positive control row name. Provide positive control positions as e.g {nl}A11+A12:A, B11+B12:B, ...')
                    if int(bg.strip().split(':')[0][1:])>12:
                        errors.append(f'Invalid positive control column number. Provide positive control positions as e.g {nl}A11+A12:A, B11+B12:B, ...')
                
            else:
                errors.append(f'Invalid positive control separator. Provide positive control positions as e.g {nl}A11+A12:A, B11+B12:B, ...')
        else:
            pass

        #Check input for lag calculation field
        if self.lag_calc_input.text()!='':
            #This field takes only a float as input - so check that input is convertible to float
            try:
                float(self.lag_calc_input.text().strip())
            except:
                errors.append('Lag calculation threshold value must be a number!')

        #Check input for lowec calculation field
        if self.lowec_calc.currentText()=='% PC lag':
            try:
                float(self.lowec_input.text())
            except:
                errors.append('Loec calculation threshold value for lag must be a number!')
            if float(self.lowec_input.text())<=100:
                errors.append('Loec calculation threshold for lag should be greater than 100%')
        
        elif self.lowec_calc.currentText()=='% PC AUC' or self.lowec_calc.currentText()=='% PC yield':
            try:
                float(self.lowec_input.text())
            except:
                errors.append('Loec calculation threshold value for AUC must be a number!')
            if float(self.lowec_input.text())>=100:
                errors.append('Loec calculation threshold for AUC should be smaller than 100%')   

        
        elif self.lowec_calc.currentText()=='ANOVA lag' or self.lowec_calc.currentText()=='ANOVA AUC' \
        or self.lowec_calc.currentText()=='ANOVA yield':
            
            #Check that there are at least 2 positive controls per strain
            if not ':' in pos:
                errors.append('Positive controls are required for statistical testing!')

            if ',' in pos:
                if '+' in pos:
                    replis=pos.split('+')
                    if len(replis)<2:
                        errors.append('minimum of 2 replicates required for statistical testing.')
                else:
                    replis=pos.split(',')
                    if '' in replis or ' ' in replis:
                        errors.append('Incorrect positive control input!')

            #Check that there are at least 2 replicates per strain
            if not ':' in reps:
                errors.append('Replicates are required for statistical testing!')

            if ',' in reps:
                replis=[len(x.split(':')) for x in reps.split(',')]
                if any(r < 2 for r in replis):
                    errors.append('minimum of 2 replicates required for statistical testing.')
            else:
                replis=reps.split(':')
                if len(replis)<2:
                    errors.append('minimum of 2 replicates required for statistical testing.')
        
        #Check input for MIC calculation field
        if self.mic_calc.currentText()!='None':
            try:
                float(self.mic_input.text())
            except:
                errors.append('MIC calculation threshold value must be a number.')

        #Check input for concentration field
        if self.concentrations.text()!='':
            if ',' in self.concentrations.text() and ':' in self.concentrations.text():
                errors.append('Provide either a list of concentrations, e.g 1, 2, 3, 4 ... , or highest concentration followed by dilution, e.g 12:4')

            elif ',' in self.concentrations.text():
                try:
                    [float(x.strip()) for x in self.concentrations.text().split(',')]
                except:
                    errors.append('List of concentrations must consist of numbers only!')

                #Check that length of list equals number of columns provided minus number of positive controls
                #This assumes that the number of positive controls is equal for all rows!
                if pos!='':
                    num_pos=len(pos.split(',')[0].split('+'))
                    if (int(self.num_cols.currentText())-num_pos)!=len(self.concentrations.text().split(',')):
                        errors.append('List of concentrations must be as long as number of used plate columns - number of positive controls per row')

            else:
                if ':' in self.concentrations.text():
                    if len(self.concentrations.text().split(':'))>2:
                        errors.append('For dilution series, provide highest concentration followed by dilution factor, e.g 12:4')
                    else:
                        try:
                            [float(x) for x in self.concentrations.text().split(':')]
                        except:
                            errors.append('Highest concentration and dilution must be provided as numbers.')
                else:
                    errors.append('Input to concentration field must be either a list of concentrations or highest concentration followed by dilution.')

        #Check that lowec calculation input is not empty
        if self.lag_calc_input.text()=='':
            errors.append('Please provide a threshold for calculating the end of the lag phase!')

        return errors
    
    def determine_replicate_setup(self, replicate_rows):
        """Determine whether replicates are defined column wise or row wise"""

        #Check whether replicates are specified by rows (such as when investigating concentration dependent effects, supplied as A:B, C:D ...),
        #or by columns (e.g when characterizing growth, supplied as A01:A02:A03, A04:A05:A06, ...)
        
        if ',' in replicate_rows:
            all_reps=[len(str(x.strip())) for r in replicate_rows.split(',') for x in r.split(':')]
            if all(x==1 for x in all_reps):
                self.reps_in_rows=True
            elif all(x==3 for x in all_reps):
                self.reps_in_cols=True

        elif ':' in replicate_rows and not ',' in replicate_rows:
            all_reps=[len(str(x.strip())) for x in replicate_rows.split(':')]
            if all(x==1 for x in all_reps):
                self.reps_in_rows=True
            elif all(x==3 for x in all_reps):
                self.reps_in_cols=True

        return self.reps_in_rows, self.reps_in_cols
    
    def average_replicates(self, df, replicate_rows):
        """Average replicate sample rows"""

        #Check whether replicates are specified by rows (such as when investigating concentration dependent effects, supplied as A:B, C:D ...),
        #or by columns (e.g when characterizing growth, supplied as A01:A02:A03, A04:A05:A06, ...)
        self.reps_in_rows, self.reps_in_cols = self.determine_replicate_setup(replicate_rows)
        
        #rename columns in to remove whitespaces, such that they match the replicate pairs
        df.rename(columns={c:c.strip() for c in df.columns}, inplace=True)

        #If replicates on plate are rows:
        if self.reps_in_rows==True and self.reps_in_cols==False:

            #parse replicate rows and average
            replicate_rows=[tuple(r.strip() for r in val.split(':')) for i, val in enumerate(replicate_rows.split(','))]
            replicate_pairs=[]

            c_nums=['0'+str(i) if len(str(i))<2 else str(i) for i in range(1, int(self.num_cols.currentText())+1)]
            for r in replicate_rows:
                replicate_pairs.extend([tuple(x+num for x in r) for num in c_nums])

            #Create dataframe
            avg_df=pd.DataFrame()
            avg_df['Hour']=df.iloc[:,0]

            #populate dataframe with averages
            for p in replicate_pairs:
                avg_df[''.join([x[0] for x in p])+str(p[0][1:3])]=df[[x for x in p]].mean(axis=1)
            
            return avg_df
        

        elif self.reps_in_cols==True and self.reps_in_rows==False:

            replicate_pairs=[tuple(r.strip() for r in val.split(':')) for i, val in enumerate(replicate_rows.split(','))]
            
            #Create dataframe
            avg_df=pd.DataFrame()
            avg_df['Hour']=df.iloc[:,0]

            #populate dataframe with averages
            for p in replicate_pairs:
                avg_df[''.join([x for x in p])]=df[[x for x in p]].mean(axis=1)
            
            return avg_df

    def substract_background(self, df, bg_rows, average):
        """Substract the background rows from sample rows. Always average the background before substraction if there are several replicates"""

        #number of columns used in the analysis
        c_nums=['0'+str(i) if len(str(i))<2 else str(i) for i in range(1, int(self.num_cols.currentText())+1)]
        #if replicate rows have been averaged

        #Remove space characters from bg_rows
        bg_rows=bg_rows.replace(' ', '')
       
        if average==True:
            #If the samples have been averaged, the the column names will be like AB01, AB02
            #Create pairs between samples and backgrounds
            bg_pairs=[]
            if ',' in bg_rows:
                for r1 in bg_rows.split(','):
                    bg_pairs.extend((r1.split(':')[0].strip()+num, r1.split(':')[1].strip()+num) for num in c_nums)
                
            else:
                bg_pairs.extend((bg_rows.split(':')[0].strip()+num, bg_rows.split(':')[1].strip()+num) for num in c_nums)

            #now substract background columns from sample columns
            sub_df=pd.DataFrame()
            sub_df['Hour']=df.iloc[:,0]
            for p in bg_pairs:
                sub_df[p[0]]=df[p[0]]-df[p[1]]
        
            return sub_df

        #If replicate rows are not averaged
        else:
            #If background has several replicates for different rows
            if ',' in bg_rows:
                if len(bg_rows.split(',')[0].split(':')[1])>1:

                    #Create tuples with pairs of columns to be averaged
                    bg_pairs=[]
                    for r in bg_rows.split(','):
                        bg_pairs.extend([tuple(x+num for x in r.split(':')[1]) for num in c_nums])
                    
                    #Calculate background averages and append to the dataframe
                    for p in bg_pairs:
                        #column name will be like CD01_bg, CD02_bg, osv
                        df[''.join([x[0] for x in p])+str(p[0][1:3])+'_bg']=df[[x for x in p]].mean(axis=1)

                    #construct pairs of unaverged columns and background columns
                    fin_pairs=[]
                    for r in bg_rows.split(','):
                        for i in range(len(r.split(':')[0])):
                            fin_pairs.extend((r[i]+num, r.split(':')[1]+num) for num in c_nums)

                    #Return dataframe with bg substracted columns
                    sub_df=pd.DataFrame()
                    sub_df['Hour']=df.iloc[:,0]
                    for p in fin_pairs:
                        sub_df[p[0]]=df[p[0]]-df[f'{p[1]}_bg']

                return sub_df
            
            #If there is one background for all samples, with several background replicates
            elif not ',' in bg_rows and len(bg_rows.split(':'))>1:
                bg_pairs=[[x+str(num) for x in bg_rows.split(':')[1].strip()] for num in c_nums]

                for p in bg_pairs:
                    #column name will be like CD01_bg, CD02_bg, osv
                    df[''.join([x[0] for x in p])+str(p[0][1:3])+'_bg']=df[[x for x in p]].mean(axis=1)   

                #construct pairs of unaveraged columns and background columns
                fin_pairs=[]
                for r in bg_rows.split(':')[0]:
                    fin_pairs.extend((r.strip()+str(num), bg_rows.split(':')[1].strip()+str(num)) for num in c_nums)

                #Return dataframe with bg substracted columns
                    sub_df=pd.DataFrame()
                    sub_df['Hour']=df.iloc[:,0]
                    for p in fin_pairs:
                        sub_df[p[0]]=df[p[0]]-df[f'{p[1]}_bg']

                return sub_df
            
            #If background is only one row #TODO: Test this!
            else:
                #create pairs and substract single bg column
                bg_pairs=[]
                for r in bg_rows:
                    for i in range(len(r.split(':')[0])):
                        bg_pairs.extend((r[i]+num, r.split(':')[1]+num) for num in c_nums)

                sub_df=pd.DataFrame()
                sub_df['Hour']=df.iloc[:,0]
                for p in bg_pairs:
                    sub_df[p[0]]=df[p[0]]-df[p[1]]
                
                return sub_df
                

    def set_to_zero(self,df): #Todo - SHOULD THIS BE KEPT?
        """Avoid negative read values - until a sequence of 5 positive values is encountered, set all values to 0"""

        #Check for each column at which index the next 5 values are > 0 - set everything before to 0
        for c in df.iloc[:,1:]:

            pos_index=0
            try:
                pos_index=[i for i, val in enumerate(pd.Series(df[c])) if all(v>=0 for v in df.loc[i:i+5, c])][0]
            except:
                pass
                #if this has not happened, set all values in the column to 0
            if pos_index>0:
                df.loc[0:pos_index, c] = 0
            else:
                df.loc[:,c] = 0
        return df


    def shift_curves(self, df):
        """Shift curves such that the first value of each curve is 0"""

        for c in df.iloc[:,1:]:
            if df.loc[0, c] < 0:
                df[c]=df[c]+abs(df.loc[0, c])
            elif df.loc[0, c] > 0:
                df[c]=df[c]-df.loc[0, c]
                
        return df
            

    def fit_gam_to_avg(self, df):
        """Fit linear GAM to curve - the model is used for smoothing, resulting in a theoretical curve 
        used for further analysis"""

        gam_df=pd.DataFrame()
        gam=LinearGAM(s(0), constraints='monotonic_inc')

        gam_df['Hour']=df['Hour']
        for c in df.iloc[:, 1:]:
            gam.fit(df.iloc[:,0], df[c])
            gam_df[c]=gam.predict(df.iloc[:,0])

        return gam_df


    def calculate_metrics(self, df):
        """Calculate growth curve metrics - AUC, length of lag phase, maximum yield, slope"""
        
        metrics={'sample':[], 'AUC':[], 'lag_len':[], 'max_yield':[], 'slope':[]}
        lag_type=self.lag_calc.currentText()
        lag_crit=float(self.lag_calc_input.text().strip())

        #Determine positive controls to be used for % max. OD lag calculation

        if ',' in self.pos_contr.text():
            pos_list=[x.strip() for x in self.pos_contr.text().split(',')]
        else:
            pos_list=[x.strip() for x in list(self.pos_contr.text())]
        
        #If replicates are to be averaged
        if self.std_calculated==True:
            if self.avg_rows.isChecked()==True:
                if ',' in self.rep_rows.text():
                    reps=[''.join([y.strip() for y in x.split(':')]) for x in self.rep_rows.text().split(',')]
                else:
                    reps=list(''.join([x.strip() for x in self.rep_rows.text().split(':')]))
        
        #Go through each column (curve) and calculate the timepoint where the threshold value is passed
        print(df.columns)
        for i, c in enumerate(df.iloc[:,1:]):

            #Append quickly calculatable metrics
            metrics['sample'].append(c)
            metrics['AUC'].append(round(auc(df.iloc[:,0], df.loc[:,c]),2))
            metrics['max_yield'].append(round(df[c].max(),2))

            #Determine positive control for the current column - if several, average them
            c_name=df.iloc[:,1:].columns[i]

            print(c, c_name)

            if '%' in lag_type:
                if self.std_calculated==True:
                    print('std calculated true')
                    if self.avg_rows.isChecked()==False:
                        pos_entry=[x for x in pos_list if c_name[:-2] in x.split(':')[1]]

                    #Find positive control columns, replicate rows and combine them  
                    else:
                        rep_fit=[r for r in reps if c_name[:-2] in r]
                        if '+' in pos_list[0]:
                            positive_columns={y[-2:] for x in pos_list for y in x.split(':')[0].split('+')}
                        else:
                            positive_columns={x[-2:] for x in pos_list}

                        pos_entry_set={r+str(x) for x in positive_columns for r in rep_fit}

                        pos_entry=['+'.join(pos_entry_set)+f':{rep_fit[0]}']

                else:
                    pos_entry=[x for x in pos_list if c_name[:-2] in x.split(':')[1]]
                    print(f'pos_entry:{pos_entry}')

                #In cases where no background rows are specified (either background rows or wrong input), set lag time to 24
                if len(pos_entry)>0:

                    #Check if there are several positive controls - If yes, extract and average
                    if '+' in pos_entry[0]:
                        pos_cols=pos_entry[0].split(':')[0].split('+')
                        pos_curve=df[pos_cols].mean(axis=1)
                    else:
                        pos_cols=pos_entry[0].split(':')[0]
                        pos_curve=df[pos_cols]

                    #Calculate end of lag phase based on selected criterion
                    
                    #Get end of lag phase based on % of max_OD. #we want the exact x at end of lag time.Therefore we get the value BEFORE threshold is reached
                    #and AFTER threshold is reached, then calculate x at y=threshold value based on y=mx+b
                    y_crit=(float(lag_crit)/100)*pos_curve.max()
                    after_end=[(i, x) for i, x in enumerate(df[c]) if x>y_crit]
                else:
                    metrics['lag_len'].append(round(24.0))

            else:
                after_end=[(i, x) for i, x in enumerate(df[c]) if x>lag_crit]
                y_crit=lag_crit

            #Check in case threshold value is never crossed
            if len(after_end)==0:
                after_end=len(df[c])-1
            else:
                after_end=after_end[0][0]
                
            #Get index of row before the one that crossed the threshold
            before_end=after_end-1
            
            #If threshold was crossed at t0, set after end to 1 and before end to 0
            if before_end<0:
                before_end=0
            if before_end==0 and after_end==0:
                after_end=1

            y2=float(df.loc[after_end, c])
            y1=float(df.loc[before_end, c])
            x2=float(df.iloc[after_end, 0])
            x1=float(df.iloc[before_end, 0])

            #calculate necessary parameters
            m=((y2-y1)/(x2-x1))+0.001
            b=y1-m*x1

            print(f'x1:{x1}, x2:{x2}, y1:{y1}, y2:{y2}, m:{m}, b:{b}')
            #Solve for x at y=lag_crit
            end_lag=(y_crit-b)/m

            #if max_OD<=15, set lag end time automatically to 24
            if df[c].max()>15:
                metrics['lag_len'].append(round(end_lag, 2))
            else:
                metrics['lag_len'].append(round(24.0))

            #Find steepest point on curve over 4 points and calculate steepest slope
            listy=list(df[c])
            listx=list(df.iloc[:,0])
            diffs=[(ind, ind+3, listy[ind+3]-listy[ind]) if ind+3<=len(listy)-1 else 'endpoint' for ind, i in enumerate(listy)]
            diffs_clean=[i for i in diffs if not i=='endpoint' and not i[2]<0]
            steepest=[i for i in diffs_clean if i[2]==max([x[2] for x in diffs_clean])]
            x1, x2, y1, y2 = listx[steepest[0][0]], listx[steepest[0][1]], listy[steepest[0][0]], listy[steepest[0][1]]
            metrics['slope'].append(round((y2-y1)/(x2-x1),2))

        #set std_calculated to false again to enable calculation cycle for std and averaged metrics without the user having to close
        #the main window
        if self.std_calculated==True:
            self.std_calculated=False

        return pd.DataFrame(metrics)
    
    def get_replicate_variance(self, df):
        """Get standard deviation between replicate curve parameters"""

        #Calculate metrics for raw data (background substracted if applicable)
        if self.bg_rows.text()!='':
            df=self.substract_background(df, self.bg_rows.text(), False)

        #Calculate metrics from previously calculated_df
        std_metrics=self.calculate_metrics(df)

        #Check whether replicates on plate are defined row or column wise
        reps_in_rows, reps_in_cols = self.determine_replicate_setup(self.rep_rows.text())

        #Get replicate groups
        if reps_in_rows==True and reps_in_cols==False:
            replicate_rows=[tuple(r.strip() for r in val.split(':')) for i, val in enumerate(self.rep_rows.text().split(','))]
            replicate_pairs=[]

            c_nums=['0'+str(i) if len(str(i))<2 else str(i) for i in range(1, int(self.num_cols.currentText())+1)]
            for r in replicate_rows:
                replicate_pairs.extend([tuple(x+num for x in r) for num in c_nums])

        elif reps_in_rows==False and reps_in_cols==True:
            replicate_pairs=[tuple(r.strip() for r in val.split(':')) for i, val in enumerate(self.rep_rows.text().split(','))]

        #Calculate replicate standard deviation for each parameter and group/concentration combination
        std_dict={'Replicate group':[], 'lag_std':[], 'auc_std':[], 'yield_std':[], 'slope_std':[]}

        for r in replicate_pairs:

            if reps_in_rows==True and reps_in_cols==False:
                rep_group=''.join([x[0] for x in r])+str(r[0][-2:])
            elif reps_in_rows==False and reps_in_cols==True:
                rep_group=''.join([x for x in r])

            group_df=std_metrics[std_metrics['sample'].isin(r)==True]
            if not group_df.empty:
                std_dict['Replicate group'].append(rep_group)

                #Append normalized standard deviation for all parameters
                std_dict['lag_std'].append(round(np.std(group_df['lag_len'])/np.mean(group_df['lag_len']),2))
                std_dict['auc_std'].append(round(np.std(group_df['AUC'])/np.mean(group_df['AUC']),2))
                std_dict['yield_std'].append(round(np.std(group_df['max_yield'])/np.mean(group_df['max_yield']),2))
                std_dict['slope_std'].append(round(np.std(group_df['slope'])/np.mean(group_df['lag_len']),2))
        
        self.std_calculated=True
        
        return std_dict


    def calculate_lowec(self, metrics):
        """Calculate loec based on user input"""

        #Parse input from lowec calculation form to get positive controls and respective row.
        if ',' in self.pos_contr.text():
            if '+' in self.pos_contr.text():
                pos_pairs={x.split(':')[1]:[y for y in x.split(':')[0].split('+')] for x in self.pos_contr.text().strip().split(',')}
            else:
                pos_pairs={x.split(':')[1]:[x.split(':')[0]] for x in self.pos_contr.text().strip().split(',')}
        else:
            if '+' in self.pos_contr.text():
                pos_pairs={x.split(':')[1]:[y for y in x.split(':')[0].split('+')] for x in list(self.pos_contr.text().strip())}
            else:
                pos_pairs={x.split(':')[1]:[x.split(':')[0]] for x in list(self.pos_contr.text().strip())}

        #get background rows
        bgs=self.bg_rows.text().replace(' ', '')
        if ',' in bgs:
            bg_rows=''.join([x.split(':')[1] for x in bgs.split(',')])
        else:
            bg_rows=bgs.split(':')[1]
        bg_rows=[*bg_rows]

        #Get all concentrations used in plate layout
        concentrations=['0'+str(c) if len(str(c))==1 else str(c) for c in range(1, int(self.num_cols.currentText())+1)]

        #Now go through dict and metrics dataframe (which contains the calculated metrics)
        #1. Get rows that contain all letters and number per sample and positive control

        lowec_list=[]
        noec_list=[]

        #make list of processed samples as to avoid analyzing the same replicate pairs multiple times
        processed_reps=[]

        for k, v in pos_pairs.items():
            if not k in processed_reps:
        
                letters=list({x.strip()[0] for x in v})
                numbers=list({x.strip()[1:] for x in v})
                pos_sample_names=[n for n in metrics['sample'] if any(l in n for l in letters) and any(num in n for num in numbers)]
                sample_names=[n for n in metrics['sample'] if k in n and not any(num in n for num in numbers)]
                
                print(f'pos_sample_names: {pos_sample_names}, sample_names: {sample_names}, letters: {letters}, numbers: {numbers}')

                #Get positive sample AUC
                pos_metrics=metrics[metrics['sample'].isin(pos_sample_names)]

                #Get respective sample names
                sample_metrics=metrics[metrics['sample'].isin(sample_names)]

                #calculate cutoff value for all positive controls separately, then get all rows where lag>lag*crit_mean and auc<auc*crit_mean.
                #Then sort
                if self.lowec_calc.currentText()=='% PC lag':
                    crit_perc=float(self.lowec_input.text())/100
                    cutoff=pos_metrics['lag_len']*crit_perc
                    crit_mean=np.mean(cutoff)
                    lowec_df=sample_metrics[sample_metrics['lag_len']>crit_mean].sort_values(by=['sample'])
                    #Plates will have different layouts, so we cannot assume that the higher concentration is always further down the plate.
                    #Therefore, find the sample where the value is above (lag)/below (AUC), but closest to the threshold
                    lowec_df['lag_cutoff_diff']=lowec_df['lag_len']-crit_mean
                    lowec=lowec_df[lowec_df['lag_cutoff_diff']==lowec_df['lag_cutoff_diff'].min()]
                    #Append these to list
                    lowec_list.append((k, lowec.iloc[0,0]))

                    #Also extract the noec (the concentration before the cutoff value is reached)
                    noec_df=sample_metrics[sample_metrics['lag_len']<crit_mean].sort_values(by=['sample'])
                    noec_df['lag_cutoff_diff']=noec_df['lag_len']-crit_mean
                    noec=noec_df[noec_df['lag_cutoff_diff']==noec_df['lag_cutoff_diff'].max()]
                    noec_list.append(noec.iloc[0, 0])

                elif self.lowec_calc.currentText()=='% PC AUC':
                    crit_perc=float(self.lowec_input.text())/100
                    cutoff=pos_metrics['AUC']*crit_perc
                    crit_mean=np.mean(cutoff)
                    lowec_df=sample_metrics[sample_metrics['AUC']<crit_mean].sort_values(by=['sample'])
                    lowec_df['AUC_cutoff_diff']=lowec_df['AUC']-crit_mean
                    lowec=lowec_df[lowec_df['AUC_cutoff_diff']==lowec_df['AUC_cutoff_diff'].max()]
                    lowec_list.append((k, lowec.iloc[0,0]))

                    noec_df=sample_metrics[sample_metrics['AUC']>crit_mean].sort_values(by=['sample'])
                    noec_df['AUC_cutoff_diff']=noec_df['AUC']-crit_mean
                    noec=noec_df[noec_df['AUC_cutoff_diff']==noec_df['AUC_cutoff_diff'].min()]
                    noec_list.append(noec.iloc[0,0])

                elif self.lowec_calc.currentText()=='% PC yield':
                    crit_perc=float(self.lowec_input.text())/100
                    cutoff=pos_metrics['max_yield']*crit_perc
                    crit_mean=np.mean(cutoff)
                    lowec_df=sample_metrics[sample_metrics['max_yield']<crit_mean].sort_values(by=['sample'])
                    lowec_df['yield_cutoff_diff']=lowec_df['max_yield']-crit_mean
                    lowec=lowec_df[lowec_df['yield_cutoff_diff']==lowec_df['yield_cutoff_diff'].max()]
                    lowec_list.append((k, lowec.iloc[0,0]))

                    noec_df=sample_metrics[sample_metrics['max_yield']>crit_mean].sort_values(by=['sample'])
                    noec_df['yield_cutoff_diff']=noec_df['max_yield']-crit_mean
                    noec=noec_df[noec_df['yield_cutoff_diff']==noec_df['yield_cutoff_diff'].min()]
                    noec_list.append(noec.iloc[0,0])

                #Perform ANOVA and post hoc test
                elif self.lowec_calc.currentText()=='ANOVA lag' or self.lowec_calc.currentText()=='ANOVA AUC' \
                or self.lowec_calc.currentText()=='ANOVA yield':
                    #Get lag values for all replicates
                    if ',' in self.rep_rows.text():
                        rep_list=[x.split(':') for x in self.rep_rows.text().replace(' ', '').split(',') if not \
                                any(b in x for b in bg_rows)]
                    else:
                        rep_list=[x.split(':') for x in self.rep_rows.text().replace(' ', '') if not \
                                any(b in x for b in bg_rows)]

                    #Go through lists of replicates
                    for x in rep_list:

                        #Create list containing all positive samples between the replicates
                        rep_pos_names=[]
                        for y in x:
                            rep_pos_names.extend(pos_pairs[y.strip()])

                        #Create dictionary containing all lag/AUC values for all replicates with the same concentration
                        rep_dict={}
                        for c in concentrations:
                        #Get all possible combinations between replicates and concentration
                            combs=[y+str(c) for y in x]
                            if self.lowec_calc.currentText()=='ANOVA lag':
                            #Extract lag values from metrics dataframe
                                comb_lags=metrics[metrics['sample'].isin(combs)]['lag_len'].values
                            elif self.lowec_calc.currentText()=='ANOVA AUC':
                                comb_lags=metrics[metrics['sample'].isin(combs)]['AUC'].values
                            elif self.lowec_calc.currentText()=='ANOVA yield':
                                comb_lags=metrics[metrics['sample'].isin(combs)]['max_yield'].values
                            rep_dict[c]=comb_lags
                            
                        #Save metrics per replicate and concentration to dataframe
                        conc_df_all=pd.DataFrame(rep_dict, index=None)

                        #Now assign the control group for dunnets test - if there are several, average them
                        #Get column numbers for positive controls
                        contr_cols=[str(x[-2:]) for x in v]

                        #Remove positive controls from conc_df_all
                        conc_df=conc_df_all[[c for c in conc_df_all.columns if not str(c[-2:]) in contr_cols]]

                        if len(contr_cols)>1:
                            conc_df['pc']=conc_df_all[contr_cols].mean(axis=1)
                        else:
                            conc_df['pc']=conc_df_all[contr_cols]

                        #Now perform ANOVA
                        #print(f'ANOVA input: {[conc_df[c] for c in [x for x in conc_df.columns]]}')
                        kwa=stats.f_oneway(*[conc_df[c] for c in [x for x in conc_df.columns]])
                        p_val=kwa[1]

                        #If p-value is <= 0.05, perform dunnets post-hoc test to identify between which groups vs control the difference is significant
                        if p_val<0.05:

                            """Replace tukeys test with Dunnets test
                            tuk=stats.tukey_hsd(*[conc_df[c] for c in [x for x in conc_df.columns]])
                            tuk_pvals=tuk.pvalue
                            """

                            tuk=stats.dunnett(*[conc_df[c] for c in [x for x in conc_df.columns] if not c=='pc'], control=np.array(conc_df['pc']))
                            tuk_pvals=tuk.pvalue

                            #IMPORTANT: following code assumes that concentrations on the plate are going from highest (left on plate) to lowest (right on plate)
                            #Either the plates have to be designed accordingly, or the code has to be adjusted

                            #get indexes of columns tested against the control, then extract the column with the highest index where p<0.05
                            #(as that will correspond to the lowest concentration where and effect is observed)
                            sig_cols=[(i, col) for i, (col, p) in enumerate(zip(conc_df.columns, tuk_pvals)) if p<0.05]
                            
                            if len(sig_cols)>0:
                                sig_cols_sorted=sig_cols.sort(key=lambda x: x[0])
                                lowec_list.append(''.join(x)+str(sig_cols[-1][1]))
                                noec_list.append(''.join(x)+conc_df.columns[sig_cols[-1][0]+1])
                            else:
                                lowec_list.append('None')
                                noec_list.append('None')
                                
                                
                            """The below code is unneccessary with dunnets test, since everything is compared to the positive control

                            #Get indexes for positive controls
                            pos_ind=[(i, c) for i, c in enumerate(conc_df.columns) if any(ps[1:3] in c for ps in rep_pos_names)]
                                
                            for ind in pos_ind:
                                #print(f'ind:{ind}')
                                #Get respective array from tuk
                                p_vals_tuk=tuk_pvals[ind[0]]
                                #print(f'p_vals_tuk:{p_vals_tuk}')
                                #Get index of all values < 0.05 and the distance of each p-values index to the index of the positive control
                                p_vals_sig=[(i, p, abs(ind[0]-i)) for i, p in enumerate(p_vals_tuk) if p<0.05]
                                #print(f'index, p, dist: {p_vals_sig}')

                                #If any p-value is <0.05, append
                                if len(p_vals_sig)>0:
                                    #Sort by last element of tuple
                                    lowec_conc=sorted(p_vals_sig, key=lambda x: x[2])[0][0]
                                    lowec_col=conc_df.columns[lowec_conc]
                                    lowec_list.append(''.join(x)+lowec_col)
                                    #This assumes that concentrations on the plate are in descending order - correct when there is time!
                                    noec_list.append(''.join(x)+conc_df.columns[lowec_conc+1])
                                else:
                                    lowec_list.append('None')
                                    noec_list.append('None')
                            """
                        else:
                            noec_list.append('None')
                            lowec_list.append('None')

                        processed_reps.extend(x)

        #Filter noec and lowec lists such that only one value per replicate group is present
        filt_lowec_list=self.filter_lowecs(lowec_list)
        filt_noec_list=self.filter_lowecs(noec_list)
        
        return [*set(filt_lowec_list)], [*set(filt_noec_list)]
    
    def filter_lowecs(self, lowec_list):
        """Filter loec/noec list such that only one value per replicate group is present.
        NOTE: This assumes that concentrations go from highest (right side of plate) to
        lowest (left side of plate)"""
        
        filtered_list=[]
        #Filter out all replicate groups in list
        rep_groups={x[:-2] for x in lowec_list if not x=='None'}

        #get largest value and append to filtered list
        for r in rep_groups:
            max_rep_val=[x for x in lowec_list if r in x and int(x[-2:])==max([int(y[-2:]) for y in lowec_list if r in y])][0]
            filtered_list.append(max_rep_val)
        
        if 'None' in lowec_list:
            filtered_list.append('None')
        
        return filtered_list


    def calculate_mic(self, metrics):
        """Calculate MIC based on input threshold value"""

        mics={'rows':[], 'MICs':[]}

        if self.mic_calc.currentText()=='max. OD':
            cutoff=float(self.mic_input.text())

        #Get unique rows for which mics should be calculated
        uniques={x[:-2] for x in metrics['sample']}

        #Get all samples for which the max_yield <= cutoff
        for u in uniques:
            mic_samps=metrics[(metrics['max_yield']<=cutoff) & (metrics['sample'].str.contains(u)==True)]['sample']
            if sorted(mic_samps)!=[]:
                #Get lowest concentration with max OD below cutoff value. #TO DATE, THIS ASSUMES THAT CONCENTRATIONS ARE ORDERED
                #FROM HIGHEST TO LOWEST ON PLATE!
                mic_conc=max([x[-2:] for x in mic_samps])
                mics['MICs'].append(mic_conc)
                mics['rows'].append(u)
            else:
                mics['MICs'].append('None')
                mics['rows'].append(u)

        return mics

class RemoveLayoutWindow(QWidget):
    """ Class for removing custom layouts"""

    def __init__(self, mainwin):

        super().__init__()

        self.setWindowTitle('Remove custom layout')
        self.initGUI(mainwin)
    
    def initGUI(self, mainwin):

        layout=QGridLayout()
        self.mainwin=mainwin

        #Define and add widgets
        msg=QLabel(f'Are you sure you want to remove {self.mainwin.layout_defaults.currentText()}?')
        self.rmbutton=QPushButton('Remove')
        self.cnclbutton=QPushButton('Cancel')

        layout.addWidget(msg, 0, 0, 1, 2)
        layout.addWidget(self.cnclbutton, 1, 0)
        layout.addWidget(self.rmbutton, 1, 1)

        #Remove layout upon click
        self.rmbutton.clicked.connect(self.remove_layout)

        #Cancel remove
        self.cnclbutton.clicked.connect(self.cancel_remove)

        self.setLayout(layout)

    def remove_layout(self):
        """ Remove selected layout from defaults"""

        #Load saved default layouts
        defaults=json.load(open(resource_path('default_layouts.txt'), 'r'))
        target=self.mainwin.layout_defaults.currentText()
        target_ind=self.mainwin.layout_defaults.findText(target)

        new_defaults={k:v for k, v in defaults.items() if not k==target}

        #Write defaults, with exception of the selected, to same file
        json.dump(new_defaults, open(resource_path('default_layouts.txt'), 'w'))

        #remove item
        self.mainwin.layout_defaults.removeItem(target_ind)

        #Close window
        self.close()

    def cancel_remove(self):
        """Cancel layout remove and return to main window"""

        self.close()
    
class AddLayoutWindow(QWidget):
    """ Class for adding custom layouts to layout selection"""

    def __init__(self, mainwin):

        super().__init__()

        self.setWindowTitle('Add custom layout')
        self.initGUI(mainwin)

    def initGUI(self, mainwin):
        """Define window look and function"""

        layout=QGridLayout()
        self.mainwin=mainwin

        #Input form for layout name
        layout_name_label=QLabel('Layout name:')
        layout_name_label.setToolTip('Provide a name for your custom layout')
        self.layout_name_input=QLineEdit()

        #Button to save layout
        save_button=QPushButton('Save')
        save_button.setToolTip('Save custom layout.')

        #Add widgets
        layout.addWidget(layout_name_label, 0, 0, alignment=Qt.AlignBottom)
        layout.addWidget(self.layout_name_input, 1, 0)
        layout.addWidget(save_button, 1, 1)

        save_button.clicked.connect(self.save_layout)

        self.setLayout(layout)

    def save_layout(self):

        """ Add new layout to file"""
        #Check data integrity
        chk=self.mainwin.check_input_integrity()
        if len(chk)>0:
            #print error message
            self.mainwin.pop_errormsg(chk)
            self.close()
        
        #Add layout values to dictionary
        new_layout={}
        new_layout['name']=self.layout_name_input.text()
        new_layout['reps']=self.mainwin.rep_rows.text()
        new_layout['bg']=self.mainwin.bg_rows.text()
        new_layout['col_num']=self.mainwin.num_cols.currentText()
        if self.mainwin.avg_rows.isChecked()==True:
            new_layout['avg']=1
        else:
            new_layout['avg']=0
        if self.mainwin.smoothen_curves.isChecked()==True:
            new_layout['smoothen']=1
        else:
            new_layout['smoothen']=0
        new_layout['pos']=self.mainwin.pos_contr.text()
        new_layout['conc']=self.mainwin.concentrations.text()
        new_layout['conc_unit']=self.mainwin.concentration_unit.text()
        new_layout['lag_calc']=self.mainwin.lag_calc.currentText()
        new_layout['lag_calc_input']=self.mainwin.lag_calc_input.text()
        new_layout['lowec_calc']=self.mainwin.lowec_calc.currentText()
        new_layout['lowec_calc_input']=self.mainwin.lowec_input.text()
        new_layout['mic_calc']=self.mainwin.mic_calc.currentText()
        new_layout['mic_calc_input']=self.mainwin.mic_input.text()

        #Read in layouts file, then add new layout to file
        if os.path.getsize(resource_path('default_layouts.txt'))>0:
            with open(resource_path('default_layouts.txt'), 'r') as f:
                layouts=json.load(f)
            f.close()
        else:
            layouts={}

        if new_layout['name'] in layouts:
            errormsg=QMessageBox()
            errormsg.setIcon(QMessageBox.Critical)
            errormsg.setText(f'{new_layout["name"]} already exists! Choose another layout name.')
            errormsg.setWindowTitle('Error')
            errormsg.exec_()

        else:
            layouts[new_layout['name']]=new_layout

            #Add new layout to combobox
            self.mainwin.layout_defaults.addItem(new_layout['name'])

            #Write new layout to file
            with open(resource_path('default_layouts.txt'), 'w') as f:
                layouts=json.dump(layouts, f)
            f.close()

            #Close window
            self.close()

class MplCanvas(FigureCanvasQTAgg):
    """Class for canvas to plot on"""

    def __init__(self, parent='None', width=7, height=7, dpi=100):
        fig=Figure(figsize=(width, height), dpi=dpi)
        fig.subplots_adjust(right=0.8)
        self.axes=fig.add_subplot(111)
        super(MplCanvas, self).__init__(fig)

class PlotWindow(QWidget):
    """Class to open a separate window for plotting the curves"""

    def __init__(self, mainwin):

        super().__init__()

        self.setWindowTitle('Plot growth curves ')
        self.initUI(mainwin)
    
    
    def initUI(self, mainwin):
        """Build plotting UI """

        layout=QGridLayout()
        
        #Add mainwin as class attribute in order to access attributes of main window
        self.mainwin=mainwin
        #Add labels and buttons to select rows and columns
        row_label=QLabel('Rows to plot:')
        col_label=QLabel('Columns to plot:')
        type_label=QLabel('Curve type:')
        type_label.setAlignment(Qt.AlignBottom)
        row_label.setAlignment(Qt.AlignBottom)
        col_label.setAlignment(Qt.AlignBottom)

        #Display pandas dataframe containing calculated metrics as string
        self.selected_metrics=QLabel()

        pltbutton=QPushButton('Plot')
        pltbutton.clicked.connect(self.plot_curves)
        spacelabel=QLabel(' ')

        savebutton=QPushButton('Save')
        savebutton.clicked.connect(self.save_results)
        savebutton.resize(100, 50)

        #Set canvas to display matplotlib plots
        self.canvas=MplCanvas(self, width=5, height=4, dpi=100)

        self.row_w=QLineEdit()
        self.col_w=QLineEdit()
        self.type_w=QComboBox()
        self.type_w.addItems(['Raw', 'Raw processed','Smoothened'])

        layout.addWidget(row_label, 0, 0)
        layout.addWidget(self.row_w, 1, 0)
        layout.addWidget(col_label, 0, 1)
        layout.addWidget(self.col_w, 1, 1)
        layout.addWidget(type_label, 2, 0)
        layout.addWidget(self.type_w, 3, 0)
        layout.addWidget(spacelabel, 4, 0, 1, 2)
        layout.addWidget(pltbutton, 5, 0, 1, 2)
        layout.addWidget(self.canvas, 6, 0, 1, 2)
        layout.addWidget(self.selected_metrics, 7, 0, 1, 2, alignment=Qt.AlignCenter)
        layout.addWidget(spacelabel, 8, 0, 1, 2)
        layout.addWidget(savebutton, 9, 0, 1, 2, alignment=Qt.AlignCenter)

        #When smoothen_curves is not checked, disable type_w, 'smoothened' option
        if self.mainwin.smoothen_curves.isChecked()==True:
            self.type_w.model().item(2).setEnabled(True)
        else:
            self.type_w.model().item(2).setEnabled(False)

        #When no background is provided, disable 'raw processed' option for curve plotting
        if self.mainwin.bg_rows.text()=='' and self.mainwin.avg_rows.isChecked()==False:
            self.type_w.model().item(1).setEnabled(False)
        elif self.mainwin.bg_rows.text()!='' or self.mainwin.avg_rows.isChecked()==True:
            self.type_w.model().item(1).setEnabled(True)

        self.setLayout(layout)

    def save_results(self):
        """ write original data and calculated curve parameters to excel file"""

        #Define output filename ending based on selected parameters
        params=[]
        if '%' in self.mainwin.lag_calc.currentText():
            lag_val=f'lag%OD{self.mainwin.lag_calc_input.text()}'
            params.append(lag_val)
        else:
            lag_val=f'lagOD{self.mainwin.lag_calc_input.text()}'
            params.append(lag_val)

        lowin=self.mainwin.lowec_calc.currentText()
        if lowin!='None':
            if 'ANOVA' in lowin:
                lowend=f'loec{lowin.replace(" ", "_")}'
                params.append(lowend)
            else:
                lowend=f'loec{lowin.replace(" ", "_")+self.mainwin.lowec_calc_input.text()}'
                params.append(lowend)

        if self.mainwin.mic_calc!='None':
            micend=f'micOD{self.mainwin.mic_input.text()}'
            params.append(micend)
        
        endname='_'.join(params)+'_curve_parameters.xlsx'
        
        #write calculated data, metric results and plot containing all rows and columns to excel
        outfile=f'{resource_path(self.mainwin.filelabel.text()).replace(".xlsx", "_"+endname)}'
        raw_data=pd.read_excel(resource_path(self.mainwin.filelabel.text()), header=10)
        if self.type_w.currentText()=='Raw':
            df=self.mainwin.df_raw
        elif self.type_w.currentText()=='Raw processed':
            df=self.mainwin.df
        elif self.type_w.currentText()=='Smoothened':
            df=self.mainwin.shifted_gams

        metric_results=self.mainwin.metrics
        conc_dict=self.mainwin.conc_dict

        #Write dataframes to outfile, with several sheets - raw data, calculated data, metrics
        writer=pd.ExcelWriter(outfile, engine='xlsxwriter')
        raw_data.to_excel(writer, sheet_name='raw_data', index=False)
        df.to_excel(writer, sheet_name='calc_data', index=False)
        metric_results.to_excel(writer, sheet_name='metrics', index=False)

        #If replicates are provided, write their standard deviation to the output file
        if self.mainwin.std_dict!=None:
            std_df=pd.DataFrame(self.mainwin.std_dict)
            std_df.to_excel(writer, sheet_name='metrics', index=False, startcol=6, startrow=0)

        if self.mainwin.lowec_calc.currentText()!='None':
            #If concentrations are provided, add a column with the respective concentration to dataframe
            if self.mainwin.concentrations.text()!='':
                low_concs=[conc_dict[x[-2:]] if x[-2:] in conc_dict else 'None' for x in sorted(self.mainwin.lowecs)]
                no_concs=[conc_dict[x[-2:]] if x[-2:] in conc_dict else 'None' for x in sorted(self.mainwin.noecs)]
                low_df=pd.DataFrame({'Loecs': sorted(self.mainwin.lowecs), 'Concentrations': low_concs})
                no_df=pd.DataFrame({'Noecs': sorted(self.mainwin.noecs), 'Concentrations':no_concs})

            else:
                low_df=pd.DataFrame({'Loecs': sorted(self.mainwin.lowecs)})
                no_df=pd.DataFrame({'Noecs': sorted(self.mainwin.noecs)})    

            low_df.to_excel(writer, sheet_name='metrics', index=False, startcol=12, startrow=0)
            no_df.to_excel(writer, sheet_name='metrics', index=False, startcol=15, startrow=0)

        if self.mainwin.mic_calc.currentText()!='None':
            if self.mainwin.concentrations.text()!='':
                mic_concs=[conc_dict[x[-2:]] if x in conc_dict else 'None' for x in self.mainwin.mics['MICs']]
                self.mainwin.mics['Concentrations']=mic_concs
            
            mic_df=pd.DataFrame(self.mainwin.mics).sort_values(by=['rows'])
            mic_df.to_excel(writer, sheet_name='metrics', index=False, startcol=18, startrow=0)

        #Write plot to file
        #Create plot of all columns to save
        fig=plt.figure(figsize=(10, 8))
        fig.subplots_adjust(right=0.8)
        ax=plt.subplot(111)

        for c in sorted([c for c in raw_data.columns if not c=='Hour']):
            ax.plot(raw_data['Hour'], raw_data[c])

        ax.set_xlabel('Hour')
        ax.set_ylabel('Omnilog Units')
        ax.legend(sorted(raw_data.columns), loc='center right', bbox_to_anchor=(1.3, 0.5))

        workbook=writer.book
        sheet=workbook.add_worksheet('plot')

        imgdata=io.BytesIO()
        fig.savefig(imgdata, dpi=300, format='png')
        sheet.insert_image(1, 1, '', {'image_data':imgdata})

        workbook.close()

 
    def check_plotinput_integrity(self):
        """Check input of plot curves"""
        row_input=self.row_w.text()
        col_input=self.col_w.text()
        allowed_letters=['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
        nl='\n'

        errors=[]
        row_error= f'Incorrect row input. Make sure to provide either{nl}a comma-separated list of single letters or, if you{nl}only want to plot one row, a single letter.'
        col_error= f'Incorrect column input. Make sure to provide either{nl}a comma-separated list of integers, a range like "1-3"{nl}or, if you only want to plot one row, a single integer.'

        #Check row input
        #1. check whether iput is comma-separated list. See that only one letter per item is provided. 
        if ',' in row_input:
            #Check that all elements only consist of one character
            avg_len=np.mean([len(x.strip()) for x in row_input.split(',')])
            if avg_len!=1:
                errors.append(row_error)
                
                
            #Check that all elements are letters
            is_letter=[x.strip().isalpha() for x in row_input.split(',')]
            if False in is_letter:
                errors.append(row_error)

            #Check that no letters other than the allowed are in input
            allowed=[True if x.strip().lower() in allowed_letters else False for x in row_input.split(',')]
            if False in allowed:
                errors.append('Invalid letter in row descriptors.')

        else:
            if len(row_input.strip())!=1:
                errors.append(row_error)

            if not row_input.strip().isalpha():
                errors.append(row_error)
            
            if not row_input.strip().lower() in allowed_letters:
                errors.append('Invalid letter in row descriptors.')

        #Check column input
        if ',' in col_input and '-' in col_input:
            errors.append('Provide either a list or a range for columns to plot.')
        if ',' in col_input or '-' in col_input:
            if ',' in col_input:
                #Check that all provided elements are integers in range(1,13)
                try:
                    int_test=[int(x) for x in col_input.split(',')]
                except:
                    errors.append(col_error)
                else:
                    right_range=[True if int(x.strip()) in range(1, 13) else False for x in col_input.split(',')]
                    if False in right_range:
                        errors.append('A column number is out of range 1-12!')

            elif '-' in col_input:
                try:
                    int_test=[int(x) for x in col_input.split('-')]
                except:
                    errors.append(col_error)
                else:
                    right_range=[True if int(x.strip()) in range(1, 13) else False for x in col_input.split('-')]
                    if False in right_range:
                        errors.append('A column number is out of range 1-12!')
        else:
            #Check that, if no list or range is provided, the provided input is an integer
            try:
                int_test=int(col_input.strip())
            except:
                errors.append(f'{col_input} is not an integer.')

        return errors

    def plot_curves(self):
        """Plot Growth curves based on plotting window input"""

        #TODO: Create data integrity test function here
        check=self.check_plotinput_integrity()
        if len(check)>0:
            #print error message
            self.mainwin.pop_errormsg(check)
            return

        #select dataframe to plot from based on user selection in QComboBox
        if self.type_w.currentText()=='Raw':
            df=self.mainwin.df_raw

            #Get input from row_w and col_w
            #row_w input: 'A,B,C,D...' or 'all'
            #col_w input: '1, 3, 6', '1-x' or 'all'
            if not self.row_w.text()=='all':
                rows=[x.strip() for x in self.row_w.text().split(',')]
            else:
                rows=list({c.strip()[0] for c in df.columns if not c =='Hour'})
            
            #Get columns as list
            if ',' in self.col_w.text() and not '-' in self.col_w.text():
                cols=['0'+str(x.strip()) if len(str(x.strip()))==1 else str(x.strip()) for x in self.col_w.text().split(',')]
                
            elif '-' in self.col_w.text():
                x=self.col_w.text().strip().split('-')[0]
                y=self.col_w.text().strip().split('-')[1]
                pre_cols=list(range(int(x), int(y)+1))
                cols=['0'+str(x) if len(str(x))==1 else str(x) for x in pre_cols]

            elif self.col_w.text()=='all':
                cols=list({c.strip()[-2:] for c in df.columns if not c=='Hour'})
            
            #TODO: case where only one column is specified
            elif len(self.col_w.text().strip())<=2:
                single_col=[self.col_w.text().strip()]
                cols=['0'+str(x.strip()) if len(str(x))==1 else str(x.strip()) for x in single_col]
            
            #Get combination of all selected rows and columns
            col_names=list({str(x.upper())+str(y) for y in cols for x in rows})

            #Check that supplied rows and columns are actually present on plate layout
            col_chk=[]
            for c in cols:
                if not int(c) in [*range(1, int(self.mainwin.num_cols.currentText())+1)]:
                    col_chk.append(f'Column {str(c)} is not defined in plate layout!')
                    self.mainwin.pop_errormsg(col_chk)
                    return

        elif self.type_w.currentText()=='Smoothened' or self.type_w.currentText()=='Raw processed':

            if self.type_w.currentText()=='Smoothened':
                df=self.mainwin.shifted_gams

            elif self.type_w.currentText()=='Raw processed':
                df=self.mainwin.df

            #Get input from row_w and col_w
            #row_w input: 'A,B,C,D...' or 'all'
            #col_w input: '1, 3, 6', '1-x' or 'all'
            if not self.row_w.text()=='all':
                #Account for column names in the GAM dataframe that have multiple row letters
                #(As this is how averaged rows are called)
                single_rows=[x.strip() for x in self.row_w.text().split(',')]
                rows=list({c.strip()[:-2] for s in single_rows for c in df.columns if s.upper() in c and not c=='Hour'})
            else:
                rows=list({c.strip()[:-2] for c in df.columns if not c =='Hour'})
            
            #Get columns as list
            if ',' in self.col_w.text() and not '-' in self.col_w.text():
                cols=['0'+str(x).strip() if len(str(x).strip())==1 else str(x).strip() for x in self.col_w.text().split(',')]

            elif '-' in self.col_w.text():
                x=self.col_w.text().strip().split('-')[0]
                y=self.col_w.text().strip().split('-')[1]
                pre_cols=[*range(int(x), int(y)+1)]
                cols=['0'+str(x).strip() if len(str(x).strip())==1 else str(x) for x in pre_cols]

            elif self.col_w.text()=='all':
                cols=list({c.strip()[-2:] for c in df.columns if not c=='Hour'})
            
            #TODO: case where only one column is specified
            elif len(self.col_w.text())<=2:
                single_col=[self.col_w.text().strip()]
                cols=['0'+str(x.strip()) if len(str(x.strip()))==1 else str(x.strip()) for x in single_col]
            
            #Get combination of all selected rows and columns
            if self.mainwin.reps_in_rows==True:
                col_names=list({str(x)+str(y) for y in cols for x in rows})
            elif self.mainwin.reps_in_cols==True:
                col_names=[c for c in df if any(r in c for r in rows) and any(col in c for col in cols)]

            #Subset metrics dataframe to contain only the specifiec columns - #Turn to string in order to display as QLabel
            sub_df=self.mainwin.metrics[self.mainwin.metrics['sample'].isin(col_names)]
            string_df=sub_df.to_string(header=True, index=False, index_names=False).split('\n')
            string_df=[[i for i in x.split(' ') if not i==''] for x in string_df]

            nl='\n'
            tb='\t'
            fin_string=''
            for i, sub_str in enumerate(string_df):
                if i==0:
                    fin_string+=f'Sample{" "*7}AUC{" "*10}lag_length{" "*3}max_yield{" "*4}slope{nl}'
                else:
                    sub_str=[str(i)+(' '*(12-len(str(i)))) for i in sub_str]
                    fin_string+='   '.join(sub_str)+'\n'
            self.selected_metrics.setText(fin_string)
            

        #Subset metrics dataframe to contain only the specifiec columns
        sub_df=self.mainwin.metrics[self.mainwin.metrics['sample'].isin(col_names)]
    
        #Clear canvas before every plot
        self.canvas.axes.cla()
        for c in sorted(col_names):
            self.canvas.axes.plot(df['Hour'], df[c])

        #Set x and y plot labels and legend. Also adjust subplot size to make sure that the legend fits into the plot
        self.canvas.axes.legend(sorted(col_names), loc='center right', bbox_to_anchor=(1.3, 0.5))
        self.canvas.axes.set_xlabel('Hour')
        self.canvas.axes.set_ylabel('OD')
        self.canvas.draw()

class BrowseFiles(QWidget):
    """Class to open a separate window for input file selection"""

    def __init__(self):
        super().__init__()
        self.left = 10
        self.top = 10
        self.width = 640
        self.height = 480
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Browse file paths')
        self.setGeometry(self.left, self.top, self.width, self.height)
        self.openFileNameDialog()
        self.show()

    def openFileNameDialog(self):
        
        dlg=QFileDialog()
        self.filename=dlg.getOpenFileName(dlg, 'Open file ', '', 'Excel files (*.xlsx *.xls)')

def main():
    """Start up GUI application"""
    app=QApplication([])

    window=MainWindow()
    window.show()

    app.exec()

if __name__=='__main__':
    main()