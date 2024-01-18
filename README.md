# BGCA - A Graphical User Interface software for Bacterial Growth Curve Analysis

BGCA is a tool written for the automated analysis of bacterial growth curves from 96 well plates. The user inputs the used plate layout through the GUI, and the supplied parameters are then 
used to calculate curve-specific parameters, such as maximum yield, maximum slope, area under the curve (AUC) and length of lag phase. If desired, ecotoxicological measures such as LOEC/NOEC and MIC
can be calculated, either based on statistical analysis of selected curve parameters or user defined cutoffs compared to control samples. The results can be explored through an interactive plotting GUI
and exported to excel for further Analysis. BGCA is designed to take diverse plate layouts into account, and has options for dealing with sample replicated, positive controls and background samples.

The BGCA interface can be run from either the command line, using ```python /path/to/main.py``` (of course replacing ```/path/to``` with the local path to ```main.py```) or on windows by running the provided .exe file (if available). This requires 
**python>=3.10**, but **python<3.12**.

**NOTE: BGCA is currently undergoing active development, so crashes and bugs, as well as minor changes in functionality might still occur.**


![bgca_GUI_example](https://github.com/EbmeyerSt/bgca/assets/11669686/1c156251-351c-4d13-b1a5-e91e233302b9)

## Currently supported plate setups

The variety of experimental setups for growth experiments in a 96 well plate is vast. The setups extensively tested with BGCA are shown below. While analysing different setups using BGCA is certainly possible, there may be bugs that have not been found yet,
which may cause BGCA to crash. 

### Dose response experimental setup

In a dose-response experimental setting, concentration gradients should go from high concentrations (left on plate) to low concentrations (right on plate). Positive controls (in this context wells containing only bacteria, no drug/chemical are refered to as positive controls) should be placed on the right end of the plate. Replicates should be organized row-wise (R1 and R2 in the figure). If background samples are present, they should be organized in the same manner as bacterial samples, row-wise.

![BGCA_dose_response_setup](https://github.com/EbmeyerSt/bgca/assets/11669686/23c06c56-616f-4c43-b124-d8b6cecb4809)

### Characterization experiments

Characterization experiments can be set up either row wise, as shown above (without positive and background samples), or column wise, as shown below. In this case, three horizontally adjacent wells provide replicates for a single bacterial sample. When using this plate layout, replicates should be provided to the BGCA interface as A01:A02:A03, A04:A05:A06, ... and so on (see section 'usage').

![BGCA_characterization_example](https://github.com/EbmeyerSt/bgca/assets/11669686/1702edba-fa59-4faa-b376-584549bf4854)


## Usage

### Input data format
BGCA is originally designed to take Omnilog time series data exported to excel as input, but can be used to analyse any time series data, if the format is adjusted such as to mirror the Omnilog output format.
The currently supported input format is as follows: An excel table with a maximum of 97 columns - The first column being named 'Hour', the following columns being a combination of the letters A-H and numbers 1-12
(8 rows on a 96 well plate, symbolized by the letters, 12 columns per row). An example input is shown in the image below, and can also be found in the provided example file (https://github.com/EbmeyerSt/bgca/blob/main/example.xlsx).

<img width="946" alt="example_input" src="https://github.com/EbmeyerSt/bgca/assets/11669686/43803b79-6adc-45ac-ba8a-2c29a5926056">

BGCA has a multitude of options to specify experimental setups. You can provide which rows or columns on the plate are replicates of one another, which ones are background samples for others, whether positive controls (in this context, meaning wells where only bacteria, but no growth modifying agent was inoculated). These setups are specified in the upper part of the BGCA main windoww, as shown below.


![BGCA_plate_layout_example](https://github.com/EbmeyerSt/bgca/assets/11669686/e25c89cc-5068-4de8-afb0-6d23ce7ec28e)


### Plate layout input formats

Specific input formats for each of the forms in the BGCA mainwindow are specified below. Note that a help text will appear for each field when hovering the mouse over the respective fields title.

**Replicates**: Replicates should be provided either row-wise or column wise. If the plate contains no replicates, this field can be left blank.
If row-wise: 'A:B, C:D, E:F, G:H' means that rows A and B ae replicates, row C and D are replicates, and so forth. Similarily, 'A:B:C:D, E:F:G:H'
would implicate that rows A, B, C and D are replicates of one another and E, F, G and H are replicates of one another.
If column wise: 'A01:A02:A03, A04:A05:A06, A07:A08:A09, ...' indicates that columns 1-3 in row A are replicates of one another, and so on.

**Background rows**: Backgrounds can to date only be provided row-wise. 'AB:CD, EF:GH' indicates that rows C and D provide the background for rows A and B, rows G and H provide the background for rows E and F.
If no background is included in the plate setup, this field should be left blank.

**Plate columns used**: Drop-down list that can be used to specify how many of the 12 plate columns are used in the plate layout.

**Average replicates**: Check to average replicate rows or columns for calculating curve parameters.

**Positive controls**: Positive controls can be provided in the following format: 'A12:A, B12:B, ...' means that wells A12 abd B12 provide the positive controls for rows A and B. If several positive controls per row are present, specify as e.g. 'A11+A12:A, B11+B12:B, ...', meaning that well A11 and A12 provide positive controls for row A, wells B11 and B12 provide the background for row B and so on.

**Smoothen curves**: Fit a generalized additive model to each curve, smoothening the curve and removing noise. The smoothened curves are then used for calculating the curve parameters. Note that these fitted curves currently are monotonic, meaning they will not model a decrease in Omnilog Units after previous increases. 

**Concentrations**: Can either be provided as a list of concentrations (e.g 1, 0.75, 0.5, 0.25, ...) or as a dilution series as 'highest_concentration:dilution' factor (e.g 12:4)
**Unit**: String that specifies the unit for the **Concentrations** field, e.g ug/ml, mg/l, etc.


### Lag/Loec/noec/MIC calculations

It is possible to select methods for the calculation of length of lag phase, LOEC/NOEC and MIC in the lower part of BGCAs main window:


![BGCA_LOEC_calc_example](https://github.com/EbmeyerSt/bgca/assets/11669686/8b7e5bff-056b-4f96-acea-cff9fb4e57db)



**Lag-time calculation**: Decide how end of lag phase should be calculated. Selecting 'OD value' and providing an integer threshold value to the 'OD value' field to the right will calculat the exact time point at which the Omnilog Units on the y-axis of the curve will pass that value. Selecting '% max. OD' and providing an integer threshold value will calculate the exact timepoint when the Omnilog Units on the y-axis pass the supplied percentage of the maximum OD.

**LOEC calculation**: Drop-down list with several available options for calculating LOEC/NOEC values, and the values are calculated based on compairison of either the calculated lag-time, the AUC or the yield (LOEC/NOEC calculation based on slope is still to be implemented). The selected parameter can then either be compared to a user-supplied cutoff value, which is a percentage of the positive control for the respective row. The lowest concentration at which the provided threshold is passed is assigned the LOEC, the next lower concentration is assigned NOEC. Alternatively ANOVA followed by tukeys post-hoc test (**Note: tukeys post-hoc test will be replaced by Dunnets test in the near future**) is performed, and the lowest concentration at which the mean of the selected parameter is significantly different (alpha<=0.05) from other curves is assigned LOEC, the next lower concentration is assigned NOEC. If no LOEC/NOEC should be calculated, select 'None' in the list.

**MIC calculation**: Select 'max. OD' (currently the only method available for MIC calculation) and provide a Omnilog Unit threshold value. The lowest concentration where the Ominlog Units never cross the specified threshold value is assigned as MIC. 

Once all fields for the calculation of the curve parameters are specified, clicking **'submit'** will calculate the curve parameters and allow the user to continue to the plotting window.

## Plotting and saving results

BGCAs plotting window allows the user to selectively, visually explore the growth data provided in the input file and asses the calculated parameters. The results can then be exported to Excel.

![plotting_window_example](https://github.com/EbmeyerSt/bgca/assets/11669686/753f74c9-e2de-4269-aaf9-ec9177bc9985)

**Rows to plot**: Takes a list of letters as input. E.g. providing 'a, b' will plot data from the rows A and B. Specifying 'Columns to plot' as well is mandatory.

**Columns to plot**: Takes a list or a range of columns to plot. E.g. '1, 2, 3, 4' or '1-4' will plot columns one to four. Specifying 'Rows to plot' as well is mandatory.

**Curve type**: Drop-down list to select the curve type to plot. **Raw** plots the raw (input) data, **Raw processed** plots the averaged and/or background-substracted data, **Smoothened** plots the smoothened curves if the respective box has been checked in the BGCA main window.

## Output

Clicking the **Save** button at the buttom of the window will export the data and calculated curve parameters to Excel. The corresponding output file has four sheets: _raw_data_(containing the raw data), _calc_data_(containing the averaged and background substracted data, if applicable), _metrics_ (containing the calculated metrics, see figure below) and _plot_ (containing a plot of all curves). 


<img width="960" alt="output_metrics_example" src="https://github.com/EbmeyerSt/bgca/assets/11669686/8f7f8835-ca80-478a-9899-471a7830953f">


## Metric calculations

This section provides details on how the output metrics ae calculated by BGCA.

**max_yield**: The maximum Omnilog Unit value of the curve.

**AUC**: Scikit-learn's auc() function is used to calculate the AUC for each curve, using the trapezoidal rule.

**lag_len**: For **% max. OD**, the exact timepoint when the OD/Omnilog Units pass the specified cutoff is calculated. This is done by determining the first measured timepoint at which the threshold value has been passed, and the measured time point just before the threshold value is passed. The exact time at which OD/Omnilog Units > threshold is then determined by calculating a straight line between the points, according to
y=mx+b, where m=(y2-y1)/(x2-x1), b=y1-m*x1 and x(threshold)=(y(threshold value)-b)/m

**slope**: Calculated through finding the greatest difference between the first and last of 4 values while using a sliding window approach over the entire curve. The slope is then (y2-y1)/(x2-x1).
