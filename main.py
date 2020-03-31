"""
COVID-19 data visualization.
"""
import csv
import os
import sys

from datetime import datetime, date
from typing import Dict, List, Optional

import matplotlib.pyplot as plot

ALIASES: Dict[str, str] = {
    "Bahamas, The": "Bahamas",
    "Czechia": "Czech Republic",
    "Russian Federation": "Russia",
    "Iran (Islamic Republic of)": "Iran",
    "Mainland China": "China",
    "Republic of Korea": "South Korea",
    "Republic of Moldova": "Moldova",
    "Korea, South": "South Korea",
    "Taiwan*": "Taiwan",
    "UK": "United Kingdom",
    "US": "United States",
}

INPUT_FILE_FORMAT: str = "%m-%d-%Y.csv"


class DataElement:
    """
    Data for a day in a country/region.
    """

    def __init__(self, confirmed: int = 0, deaths: int = 0, recovered: int = 0):
        """
        :param confirmed: number of confirmed cases
        :param deaths: number of confirmed deaths
        :param recovered: number of people recovered
        """
        self.confirmed: int = confirmed
        self.deaths: int = deaths
        self.recovered: int = recovered

    def add(self, other: "DataElement") -> None:
        """
        Combine current data element with the other.
        """
        self.confirmed += other.confirmed
        self.deaths += other.deaths
        self.recovered += other.recovered


class CountryData:
    """
    Data for one country.
    """

    def __init__(self, name: str):
        """
        :param name: country name
        """
        self.data: Dict[date, DataElement] = {}
        self.name = name

    def add(self, time: date, element: DataElement) -> None:
        """
        Add data for a day.

        :param time: day
        :param element: data values for that day
        """
        if time not in self.data:
            self.data[time] = DataElement()
        self.data[time].add(element)

    def get_last(self) -> DataElement:
        """
        Get data for the last day.
        """
        return self.data[sorted(self.data.keys())[-1]]

    def get_data(self, average=0) -> (List[int], List[int]):
        """
        Construct data for plotting.

        :return: x axis data, y axis data
        """
        x_data: List[int] = []
        y_data: List[int] = []

        last_value: int = 0

        first_100_index = 0
        for time in sorted(self.data.keys()):
            if self.data[time].confirmed > 100:
                break
            first_100_index += 1

        for index in range(len(self.data) - average):
            x_data.append(index - first_100_index)

        for time in sorted(self.data.keys()):
            value = self.data[time].confirmed
            y_data.append(value - last_value)
            last_value = value

        y_average: List[float] = [0.0] * (len(y_data) - average)

        for index in range(len(y_data) - average):
            y_average[index] = \
                sum(y_data[index:index + average + 1]) / (average + 1)

        return x_data, y_average


class Data:
    """
    Data for all countries for all time.
    """

    def __init__(self, directory: str):
        """
        :param directory: path to directory with input CSV files
        """
        self.data: Dict[str, CountryData] = {}

        for input_file_name in os.listdir(directory):  # type: str
            if not input_file_name.endswith(".csv"):
                continue
            date_time = datetime.strptime(input_file_name, INPUT_FILE_FORMAT)
            with open(os.path.join(directory, input_file_name)) as input_file:
                self.process_file(input_file, date_time)

        self.add("China", date(2020, 1, 17), DataElement(17, 0, 0))
        self.add("China", date(2020, 1, 18), DataElement(59, 0, 0))
        self.add("China", date(2020, 1, 19), DataElement(77, 0, 0))
        self.add("China", date(2020, 1, 20), DataElement(77, 0, 0))
        self.add("China", date(2020, 1, 21), DataElement(149, 0, 0))

    def process_file(self, input_file, date_time: datetime) -> None:
        """
        Load data from file.

        :param input_file: input CSV file
        :param date_time: date derived from the file name
        """
        reader = csv.reader(input_file, delimiter=",", quotechar='"')
        header: List[str] = next(reader, None)

        for parts in reader:  # type: List[str]
            dictionary = {}
            for index, element in enumerate(header):  # type: int, str
                dictionary[element] = parts[index]
            country: str = find_key(
                dictionary, ["Country/Region", "Country_Region"]).strip()
            country = ALIASES[country] if country in ALIASES else country
            confirmed: int = \
                int(dictionary["Confirmed"]) if dictionary["Confirmed"] else 0
            deaths: int = \
                int(dictionary["Deaths"]) if dictionary["Deaths"] else 0
            recovered: int = \
                int(dictionary["Recovered"]) if dictionary["Recovered"] else 0

            self.add(country, date_time.date(),
                     DataElement(confirmed, deaths, recovered))

    def add(self, country: str, time: date, element: DataElement) -> None:
        """
        Add data for a country and a date.

        :param country: country name
        :param time: date
        :param element: data element
        """
        if country not in self.data:
            self.data[country] = CountryData(country)
        self.data[country].add(time, element)

    def get_countries(self) -> List[CountryData]:
        """
        Get data for all countries sorted by the total confirmed cases.
        """
        return sorted(self.data.values(), key=lambda x: -x.get_last().confirmed)


def find_key(dictionary: Dict[str, str], keys) -> Optional[str]:
    """
    Find value in dictionary.

    :param dictionary: input dictionary
    :param keys: keys to try
    """
    for key in keys:  # type: str
        if key in dictionary:
            return dictionary[key]

    return None


class Plotter:
    """
    Draw data using Matplotlib.
    """

    def __init__(self, data: Data, main_country: str,
                 is_logarithmic: bool, filter_, average: int):
        """
        :param data: data to plot
        :param main_country: show this country on the foreground using line with
            increased width
        :param is_logarithmic: make y axis logarithmic
        """
        self.data = data
        self.main_country = main_country
        self.is_logarithmic = is_logarithmic
        self.filter_ = filter_
        self.average = average

    def draw(self):
        """
        Plot data.
        """
        plot.figure(figsize=(1000 / 96, 600 / 96))

        for country_data in self.data.get_countries():
            if self.filter_(country_data) \
                    and country_data.name not in ["Others", self.main_country]:
                x_data, y_data = country_data.get_data(self.average)
                plot.plot(x_data, y_data, color="#CCCCCC", linewidth=0.5)

        for country_data in self.data.get_countries():
            if not self.filter_(country_data) \
                    and country_data.name not in ["Others", self.main_country]:
                x_data, y_data = country_data.get_data(self.average)
                plot.plot(x_data, y_data, label=country_data.name, linewidth=1)

        x_data, y_data = \
            self.data.data[self.main_country].get_data(self.average)
        plot.plot(x_data, y_data, color="#FFFFFF", linewidth=7)
        plot.plot(x_data, y_data, color="#4466CC", linewidth=3,
                  label=self.main_country)

        if self.is_logarithmic:
            plot.yscale("log")
        plot.title(
            f"COVID-19 confirmed cases per day, {self.average + 1} days "
            f"average, updated {datetime.now().strftime('%d %B %Y')}")
        plot.xlim([-10, 70])
        if self.is_logarithmic:
            plot.ylim([10, 100000])
        plot.ylabel("Number of confirmed cases per day")
        plot.xlabel("Days since 100th case")
        plot.legend(frameon=False)
        plot.savefig("output.png")


if __name__ == "__main__":

    country_argument: str = sys.argv[1]

    input_directory: str = "csse_covid_19_data/csse_covid_19_daily_reports"
    if len(sys.argv) > 2:
        input_directory: str = sys.argv[2]

    Plotter(
        Data(input_directory), main_country=country_argument,
        is_logarithmic=True,
        filter_=lambda country_data: country_data.get_last().confirmed < 10000,
        average=4).draw()
