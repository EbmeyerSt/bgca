# BGCA - A Graphical User Interface software for Bacterial Growth Curve Analysis

BGCA is a tool written for the automated analysis of bacterial growth curves from 96 well plates. The user inputs the used plate layout through the GUI, and the supplied parameters are then 
used to calculate curve-specific parameters, such as maximum yield, maximum slope, area under the curve (AUC) and length of lag phase. If desired, ecotoxicological measures such as LOEC/NOEC and MIC
can be calculated, either based on statistical analysis of selected curve parameters or user defined cutoffs compared to control samples. The results can be explored through an interactive plotting GUI
and exported to excel for further Analysis. BGCA is designed to take diverse plate layouts into account, and has options for dealing with sample replicated, positive controls and background samples.

**NOTE: BGCA is currently undergoing active development, so crashes and bugs, as well as minor changes in functionality might still occur**

## Usage

### Input data format
BGCA is originally designed to take Omnilog time series data exported to excel as input, but can be used to analyse any time series data, if the format is adjusted such as to mirror the Omnilog output format.
The currently supported input format is as follows: An excel table with a maximum of 97 columns - The first column being named 'Hour', the following columns being a combination of the letters A-H and numbers 1-12
(8 rows on a 96 well plate, symbolized by the letters, 12 columns per row). An example input is shown in the image below
