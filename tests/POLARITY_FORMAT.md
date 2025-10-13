# Vensim MDL Polarity Format

## Connection Line Format

Connections in Vensim MDL files (Type 1 lines) have this structure:

```
1,id,from_id,to_id,shape,hidden,thickness,font_size,color_r,color_g,color_b,polarity_code,delay_mark,waypoints
```

## Polarity Field

The **polarity_code** field (position 12) controls whether the connection shows a `+` or `-` sign:

### Positive Polarity (Default)
- **Value**: `0`
- **Display**: Shows `+` sign or no sign
- **Meaning**: Increase in source causes increase in target

**Example:**
```
1,23,5,6,1,0,0,0,0,64,0,-1--1--1,,1|(625,325)|
```
Connection from variable 5 to variable 6 with **positive** polarity (field value = `0`)

### Negative Polarity
- **Value**: `43`
- **Display**: Shows `-` sign
- **Meaning**: Increase in source causes decrease in target

**Example:**
```
1,26,7,8,1,0,43,0,0,64,1,-1--1--1,,1|(325,400)|
```
Connection from variable 7 to variable 8 with **negative** polarity (field value = `43`)

## Test File

See `test_polarity.mdl` for a complete working example with both polarities:

- **Positive connections**: Population → Birth Rate, Population → Death Rate
- **Negative connections**:
  - Carrying Capacity → Growth Pressure (inverse relationship)
  - Crowding Effect → Adjusted Birth Rate (reduces birth rate)

## Implementation Notes

When generating MDL files programmatically:

```python
# Positive polarity
connection_line = f"1,{conn_id},{from_id},{to_id},0,0,0,22,0,192,0,-1--1--1,,1|(0,0)|"

# Negative polarity
connection_line = f"1,{conn_id},{from_id},{to_id},0,0,43,22,0,192,1,-1--1--1,,1|(0,0)|"
#                                                    ^^            ^
#                                                    |             |
#                                        thickness=43 (neg)   polarity flag=1
```

**Note**: When using negative polarity (43), also set the polarity flag (position 11) to `1`.
