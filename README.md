# BGCA - A Graphical User Interface software for Bacterial Growth Curve Analysis

BGCA is a tool written for the automated analysis of bacterial growth curves from 96 well plates. The user inputs the used plate layout through the GUI, and the supplied parameters are then 
used to calculate curve-specific parameters, such as maximum yield, maximum slope, area under the curve (AUC) and length of lag phase. If desired, ecotoxicological measures such as LOEC/NOEC and MIC
can be calculated, either based on statistical analysis of selected curve parameters or user defined cutoffs compared to control samples. The results can be explored through an interactive plotting GUI
and exported to excel for further Analysis. BGCA is designed to take diverse plate layouts into account, and has options for dealing with sample replicated, positive controls and background samples.

![bgca_GUI_example](https://github.com/EbmeyerSt/bgca/assets/11669686/1c156251-351c-4d13-b1a5-e91e233302b9)

**NOTE: BGCA is currently undergoing active development, so crashes and bugs, as well as minor changes in functionality might still occur.**

## Usage

### Input data format
BGCA is originally designed to take Omnilog time series data exported to excel as input, but can be used to analyse any time series data, if the format is adjusted such as to mirror the Omnilog output format.
The currently supported input format is as follows: An excel table with a maximum of 97 columns - The first column being named 'Hour', the following columns being a combination of the letters A-H and numbers 1-12
(8 rows on a 96 well plate, symbolized by the letters, 12 columns per row). An example input is shown in the image below, and can also be found in the provided example file (https://github.com/EbmeyerSt/bgca/blob/main/example.xlsx).

<img width="946" alt="example_input" src="https://github.com/EbmeyerSt/bgca/assets/11669686/43803b79-6adc-45ac-ba8a-2c29a5926056">

BGCA has a multitude of options to specify experimental setups. You can provide which rows or columns on the plate are replicates of one another, which ones are background samples for others, whether positive controls (in this context, meaning wells where only bacteria, but no growth modifying agent was inoculated). These setups are specified in the upper part of the BGCA main windoww, as shown below.

![BGCA_plate_layout_example](https://github.com/EbmeyerSt/bgca/assets/11669686/e25c89cc-5068-4de8-afb0-6d23ce7ec28e)

### Plate layout input formats

Specific input formats for each of the forms in the BGCA mainwindow are specified below:

**Replicates**: Replicates should be provided either row-wise or column wise. If the plate contains no replicates, this field can be left blank.
If row-wise: 'A:B, C:D, E:F, G:H' means that rows A and B ae replicates, row C and D are replicates, and so forth. Similarily, 'A:B:C:D, E:F:G:H'
would implicate that rows A, B, C and D are replicates of one another and E, F, G and H are replicates of one another.
If column wise: 'A01:A02:A03, A04:A05:A06, A07:A08:A09, ...' indicates that columns 1-3 in row A are replicates of one another, and so on.

**Background rows**: Backgrounds can to date only be provided row-wise. 'AB:CD, EF:GH' indicates that rows C and D provide the background for rows A and B, rows G and H provide the background for rows E and F.
If no background is included in the plate setup, this field should be left blank.
