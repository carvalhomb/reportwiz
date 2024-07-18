# Tables Metadata

## temperatures

- Table name: temperatures
- Description: NASA/POWER CERES/MERRA2 Native Resolution Daily Data
- API: POWER Daily API, version v2.5.9
- Sources: "ceres", "flashflux", "syn1deg", "merra2", "power"
- Fill value for empty cells: -999.0
- Start date: "20220101"
- End date: "20240714"
- Columns:
    * T2M: Temperature at 2 Meters in degrees Celsius (C)
    * T2MDEW: Dew/Frost Point at 2 Meters in degrees Celsius (C)
    * T2MWET: Wet Bulb Temperature at 2 Meters in degrees Celsius (C)
    * TS: Earth Skin Temperature in degrees Celsius (C)
    * T2M_RANGE: Temperature at 2 Meters Range in degrees Celsius (C)
    * T2M_MAX: Temperature at 2 Meters Maximum in degrees Celsius (C)
    * T2M_MIN: Temperature at 2 Meters Minimum in degrees Celsius (C)
    * ALLSKY_SFC_SW_DWN: All Sky Surface Shortwave Downward Irradiance in megajoules per square meter per day (MJ/m^2/day)
    * CLRSKY_SFC_SW_DWN: Clear Sky Surface Shortwave Downward Irradiance in megajoules per square meter per day (MJ/m^2/day)
    * ALLSKY_KT: All Sky Insolation Clearness Index (dimensionless)
    * ALLSKY_SFC_LW_DWN: All Sky Surface Longwave Downward Irradiance in watts per square meter (W/m^2)
    * ALLSKY_SFC_PAR_TOT: All Sky Surface PAR Total in watts per square meter (W/m^2)
    * CLRSKY_SFC_PAR_TOT: Clear Sky Surface PAR Total in watts per square meter (W/m^2)
    * ALLSKY_SFC_UVA: All Sky Surface UVA Irradiance in watts per square meter (W/m^2)
    * ALLSKY_SFC_UVB: All Sky Surface UVB Irradiance in watts per square meter (W/m^2)
    * ALLSKY_SFC_UV_INDEX: All Sky Surface UV Index (dimensionless)

## ee

- Table name: ee
- Description: 
- API: Unknown
- Sources: HEP smart meter
- Fill value for empty cells: None
- Start date: "20220502"
- End date: "20240715"
- Columns:
    * year: 
    * month:
    * day:
    * SolarPower:
    * Nocna_Poslano:
    * Nocna_Preuzeto:
    * Dnevna_Preuzeto:
    * Dnevna_Poslano:
    * Preuzeto_total:
    * Poslano_total:
    * UkupnaPotrosnja:
    * Predano/Utroseno:

## hep_final

- Table name: hep_final
- Description: 
- API: Unknown
- Sources: HEP smart meter
- Fill value for empty cells: None
- Start date: "20220502"
- End date: "20240715"
- Columns:
    * year: 
    * month:
    * day:
    * Nocna_Poslano:
    * Nocna_Preuzeto:
    * Dnevna_Preuzeto:
    * Dnevna_Poslano:


## hep

- Table name: hep
- Description: 
- API: Unknown
- Sources: HEP smart meter
- Fill value for empty cells: None
- Start date: "20220502"
- End date: "20240715"
- Columns:
    * Mjerno mjesto: 
    * Datum:
    * Vrijeme:
    * Brojilo:
    * Vrijednost snaga:
    * Vrijednost energija:
    * Godisnje doba:
    * Tarifa:
    * Smjer:
