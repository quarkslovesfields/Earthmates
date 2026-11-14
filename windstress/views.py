
from django.shortcuts import render
from django.http import HttpResponse
from django.conf import settings

import os
import io
import base64
import matplotlib.pyplot as plt

from .processing import (
    load_wind_stress,
    plot_wind_stress_map,
    plot_wind_stress_timeseries,
)


def figure_to_base64(fig):
    buffer = io.BytesIO()

    fig.savefig(
        buffer,
        format="png",
        dpi=150,
        bbox_inches="tight"
    )

    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    plt.close(fig)

    return image_base64


def home(request):
    context = {}

    if request.method == "POST":
        start_month = request.POST.get("start_month")
        end_month = request.POST.get("end_month")

        try:
            data = load_wind_stress(start_month, end_month)

            # Generate spatial map
            map_fig = plot_wind_stress_map(data)
            map_image = figure_to_base64(map_fig)

            # Generate time series
            timeseries_fig = plot_wind_stress_timeseries(data)
            timeseries_image = figure_to_base64(timeseries_fig)

            context["success"] = True
            context["start_month"] = start_month
            context["end_month"] = end_month
            context["message"] = (
                f"Successfully loaded {len(data.time)} months of data."
            )

            context["map_image"] = map_image
            context["timeseries_image"] = timeseries_image

        except Exception as e:
            context["error"] = str(e)

    return render(request, "index.html", context)


