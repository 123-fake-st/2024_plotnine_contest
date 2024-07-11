"""
Generate a 7-day forecast with plotnine

The input file should be a .csv with these columns: Day, Low, High, Conditions

Possible weather icons for the Conditions are: cloudy, cold, drizzle, heavy rain, hot, partly cloudy, rain, snow, sunny,
thunderstorm, windy

Example .csv file:
Day,Low,High,Conditions
Today,65,77,Cloudy
Mon,61,84,Sunny
Tue,67,93,Hot
Wed,59,76,Drizzle
Thu,54,75,Windy
Fri,57,81,Partly cloudy
Sat,60,71,Heavy rain
"""

import os, warnings
import polars as pl
import plotnine as p9

def plot_forecast(forecast: str, location: str, outfile: str) -> None:
    """
    Generate forecast plot and save to file

    Parameters
    ----------
    forecast : str | pathlib.Path
        Path to the forecast data file
    location : str
        Name of the location for the forecast; used as plot title
    outfile : str
        Path to save plot to
    """
    # import data
    raw_data = pl.read_csv(forecast)
    raw_data = raw_data.with_columns(pl.col('Day').cast(pl.Categorical))
    low_high = [raw_data.get_column('Low').min(), raw_data.get_column('High').max()]

    # daily temperature range data
    plot_data = (
        raw_data
        .with_columns(
            Temperature = pl.int_ranges(pl.col('Low') * 10, pl.col('High') * 10 + 1).list.eval(pl.element() / 10)
        )
        .select('Day', 'Conditions', 'Temperature')
        .explode('Temperature')
    )

    # underlayment data
    temp_range = pl.DataFrame({
        'Day': raw_data.get_column('Day'),
        'Temperature': [low_high] * len(raw_data)
    }).explode('Temperature')

    # text label data
    x_offset = (low_high[1] - low_high[0]) * .128  # Narrow ranges (e.g. Singapore) needed a calculated value rather than a static value (i.e. 5)
    temp_labels = (
        raw_data
        .melt(id_vars=['Day', 'Conditions'], value_vars=['Low', 'High'], value_name='temperature')
        .with_columns(
            (pl.col('temperature').cast(str) + pl.lit('°')).alias('label'),
            pl.when(pl.col('variable') == 'Low')
            .then(pl.lit(low_high[0]) - x_offset)
            .otherwise(pl.lit(low_high[1]) + x_offset)
            .alias('x')
        )
        .sort('Day')
    )

    # generate plot minus icons
    range_bg = 'xkcd:dark blue grey'
    font_size = 18
    font_family = 'Arial' # default is Helvetica; I think Arial looks a tiny bit better
    plot = (
        p9.ggplot(plot_data, p9.aes(x='Temperature', y='Day'))
        + p9.labs(title=location, subtitle="7-day forecast", x="", y="")
        + p9.geom_path(data=temp_range, size=9, color=range_bg, lineend='round', alpha=0.8)
        + p9.geom_path(p9.aes(color='Temperature'), size=8, lineend='round')
        + p9.geom_text(data=temp_labels, mapping=p9.aes(x='x', label='label'), color='white', size=font_size, ha='center', va='center')
        + p9.scale_color_gradientn(colors=['deepskyblue', 'aqua', 'palegreen', 'yellow', 'orange', 'red'], limits=[0, 100])
        + p9.scale_y_discrete(limits=raw_data['Day'].reverse().to_list(), expand=(0, 0.5, 0, 0.4))
        + p9.scale_x_continuous(expand=(0.06, 0, 0.06, 0))  # this differs from the jupyter notebook: accommodate text labels where high was 3 digits
        + p9.theme_void()
        + p9.theme(
            text=p9.element_text(family=font_family, color='white'),
            plot_background=p9.element_rect(fill='royalblue'),
            plot_title=p9.element_text(size=24),
            plot_subtitle=p9.element_text(size=16, ha='center'),
            plot_margin_top=0.05,
            plot_margin_right=0.04,
            plot_margin_bottom=0.03,
            plot_margin_left=-0.05,
            axis_text_y=p9.element_text(angle=0, size=font_size, va='center', ha='left', margin={'t': 0, 'r': 95, 'b': 0, 'l': 0, 'units': 'pt'}),
            axis_text_x=p9.element_blank(),
            legend_position='none',
        )
    )

    # add icons to plot
    xo = 120
    yo_max = 509
    yo_mod = 78
    rows = raw_data.rows(named=True)
    for i, row in enumerate(rows):
        yo = yo_max - i * yo_mod
        plot = (
            plot 
            + p9.watermark(f'./img/{row["Conditions"].lower().replace(" ", "_")}_32px.png', xo=xo, yo=yo)
        )

    if os.path.isfile(outfile):
        warnings.warn('Existing plot will be overwritten')
    plot.save(
        outfile,
        width=6.5,
        height=6.5,
        dpi=100,
    )