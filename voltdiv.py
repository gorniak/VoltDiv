# @file voltdiv.py
#
# @brief Calcuator for the optimal resitiors values for voltage divider of feedback circuit of voltage regulator
#
# @section Author
# - Created by Radoslaw Gorniak on 2022-06-05.
#
# License CC BY 4.0

## STEP 1 - set the required output voltage
VOLTAGE_OUTPUT = 3.3            # in Volts

## STEP 2 - set the reference voltage of feedback circuit
VOLTAGE_REFERENCE = 1           # in Volts

## STEP 3a - Select (uncomment) one of following resistor series

#E24 resistance serie
#resistance_values_serie = [100, 110, 120, 130, 150, 160, 180, 200, 220, 240, 270, 300, 330, 360, 390, 430, 470, 510, 560, 620, 680, 750, 820, 910]

#E48 resistance serie
#resistance_values_serie = [100, 105, 110, 115, 121, 127, 133, 140, 147, 154, 162, 169, 178, 187, 196, 205, 215, 226, 237, 249, 261, 274, 287, 301, 316, 332, 348, 365, 383, 402, 422, 442, 464, 487, 511, 536, 562, 590, 619, 649, 681, 715, 750, 787, 825, 866, 909, 953]

#E96 resistance serie
#resistance_values_serie = [100, 102, 105, 107, 110, 113, 115, 118, 121, 124, 127, 130, 133, 137, 140, 143, 147, 150, 154, 158, 162, 165, 169, 174, 178, 182, 187, 191, 196, 200, 205, 210, 215, 221, 226, 232, 237, 243, 249, 255, 261, 267, 274, 280, 287, 294, 301, 309, 316, 324, 332, 340, 348, 357, 365, 374, 383, 392, 402, 412, 422, 432, 442, 453, 464, 475, 487, 499, 511, 523, 536, 549, 562, 576, 590, 604, 619, 634, 649, 665, 681, 698, 715, 732, 750, 768, 787, 806, 825, 845, 866, 887, 909, 931, 953, 976]

#E24 and E48 resistance series
#resistance_values_serie = [100, 105, 110, 115, 120, 121, 127, 130, 133, 140, 147, 150, 154, 160, 162, 169, 178, 180, 187, 196, 200, 205, 215, 220, 226, 237, 240, 249, 261, 270, 274, 287, 300, 301, 316, 330, 332, 348, 360, 365, 383, 390, 402, 422, 430, 442, 464, 470, 487, 510, 511, 536, 560, 562, 590, 619, 620, 649, 680, 681, 715, 750, 787, 820, 825, 866, 909, 910, 953]

#E24 and E96 resistance series
resistance_values_serie = [100, 102, 105, 107, 110, 113, 115, 118, 120, 121, 124, 127, 130, 133, 137, 140, 143, 147, 150, 154, 158, 160, 162, 165, 169, 174, 178, 180, 182, 187, 191, 196, 200, 205, 210, 215, 220, 221, 226, 232, 237, 240, 243, 249, 255, 261, 267, 270, 274, 280, 287, 294, 300, 301, 309, 316, 324, 330, 332, 340, 348, 357, 360, 365, 374, 383, 390, 392, 402, 412, 422, 430, 432, 442, 453, 464, 470, 475, 487, 499, 510, 511, 523, 536, 549, 560, 562, 576, 590, 604, 619, 620, 634, 649, 665, 680, 681, 698, 715, 732, 750, 768, 787, 806, 820, 825, 845, 866, 887, 909, 910, 931, 953, 976]

## STEP 3b - or set you owns list of resistance values in Ohms in your project
resistance_values = []           # in Ohm

## STEP 4 - configure CSV file
filename = "voltdiv_out.csv"
COLUMN_SEPARATION = ';'
DECIMAL_POINT = ','

## Other configuration option
MINIMUM_RESISTANCE = 1000       # in Ohm
MAXIMUM_RESISTANCE = 100000     # in Ohm

## DEBUG
# To print debug lines uncomment the line below
#DEBUG = 1
try: DEBUG
except NameError: DEBUG = 0


# Variable lists for calculation use
resistance_values_top_ideal = []
resistance_values_top = []
resistance_values_bottom = []
result_table = []

def output_voltage(top_resistance, bottom_resistance):
    return (VOLTAGE_REFERENCE * ( (top_resistance + bottom_resistance) / bottom_resistance))


# Prepare resistance values list based on thte resitance series if the list is not defined with exact values
if len(resistance_values) == 0:
    if len(resistance_values_serie) > 0:
        for i in range(-3, 6):
            for j in resistance_values_serie:
                resistance = j*pow(10, i)
                if ((resistance >= MINIMUM_RESISTANCE)
                  and (resistance <= MAXIMUM_RESISTANCE)):
                    resistance_values.append(resistance)
    else:
        print("Set the parameters properly")
        quit()
else:
    # Sort resistance values 
    resistance_values.sort()   
if DEBUG != 0:
    print(resistance_values)


# Prepare the list in reverser order
resistance_values_reversed = resistance_values[::-1]
if DEBUG != 0:
    print(resistance_values_reversed)


# Calculate ideal resistance value for top resistor for each bottom resistor
for k in resistance_values:
    resistance_values_top_ideal.append(k*((VOLTAGE_OUTPUT/VOLTAGE_REFERENCE)-1))
if DEBUG != 0:
    print(resistance_values_top_ideal)


# Prepare the list with resistance values of bottom resistor doulbled - for each bottom reistor value the lower and hogher value of top resistance will be calcualted
for l in resistance_values:
    for ll in range(0, 2):
        resistance_values_bottom.append(l)
if DEBUG != 0:
    print(resistance_values_bottom)


# Prepare the list of resistance values of top resistor with lower and higher (or equal) value of top resistor close to ideal resistance value calculated 
no_of_max_resistance_in_list = 0
MAXIMUIM_RESISTANCE_IN_LIST = 5
for m in resistance_values_top_ideal:
    for n in resistance_values_reversed:
            if n <= m:
                if n == MAXIMUM_RESISTANCE:
                    no_of_max_resistance_in_list = no_of_max_resistance_in_list + 1
                    if no_of_max_resistance_in_list > MAXIMUIM_RESISTANCE_IN_LIST:
                        break
                    else:
                        resistance_values_top.append(n)
                else:
                    resistance_values_top.append(n)
                break
    for o in resistance_values:
            if o >= m:
                if o == MAXIMUM_RESISTANCE:
                    no_of_max_resistance_in_list = no_of_max_resistance_in_list + 1
                    if no_of_max_resistance_in_list > MAXIMUIM_RESISTANCE_IN_LIST:
                        break
                    else:
                        resistance_values_top.append(o)
                else:
                    resistance_values_top.append(o)
                break        
if DEBUG != 0:
    print(resistance_values_top)


# Main callucations
for p in range(0,len(resistance_values_top)):
    result_table.append(p)
    result_table[p] = [resistance_values_top[p],
        resistance_values_bottom[p],
        output_voltage(resistance_values_top[p], resistance_values_bottom[p]), 
        abs((output_voltage(resistance_values_top[p], resistance_values_bottom[p]) - VOLTAGE_OUTPUT)) ]
if DEBUG != 0:
    print(result_table)
    
    
# Create CSV file with sorted values
def sorted_column(value):
    return value[3]
with open(filename, 'w') as f:
    print("Required output voltage = " + str(VOLTAGE_OUTPUT) + " V\n")
    f.write("Required output voltage;;{};V\n\n".format(VOLTAGE_OUTPUT))
    print("R_TOP [Ohm];R_BOT [Ohm];V_ OUT [V];ERR [V]\n")
    f.write("R_TOP [Ohm];R_BOT [Ohm];V_OUT [V];ERR [V]\n")
    result_table.sort(key=sorted_column)
    for q in result_table:
        q[3] = (output_voltage(q[0], q[1]) - VOLTAGE_OUTPUT)
        print(";".join(str(r) for r in q))
        print(";".join(str(r) for r in q), file=f)
    f.close()


# Change column separation char to other tham ';'
if COLUMN_SEPARATION != ';':
    # Read CSV file
    with open(filename, 'r') as f:
        file = f.read()
    # Replace column separation char to selected
    file = file.replace(';', COLUMN_SEPARATION)
    f.close()    
    # Write the file out again
    with open(filename, 'w') as f:
        f.write(file)
    f.close()

    
# Change decimal point form '.' to ','
if DECIMAL_POINT == ',':
    # Read CSV file
    with open(filename, 'r') as f:
        file = f.read()
    # Replace the decimal point
    file = file.replace('.', ',')
    f.close()
    # Save CSV file
    with open(filename, 'w') as f:
        f.write(file)
    f.close()

    
# End of script
print("\nDONE")