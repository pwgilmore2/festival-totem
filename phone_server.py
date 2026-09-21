import json
import socket
import threading

from http.server import (
    BaseHTTPRequestHandler,
    ThreadingHTTPServer,
)

from queue import (
    Queue,
    Empty,
)


# ============================================================
# PHONE WEB PAGE
# ============================================================

PHONE_HTML = r'''
<!doctype html>

<html>

<head>

<meta charset="utf-8">

<meta
    name="viewport"
    content="
        width=device-width,
        initial-scale=1,
        maximum-scale=1,
        user-scalable=no
    "
>

<title>Festival Totem</title>


<style>

:root {
    color-scheme: dark;
}

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    padding: 16px;

    background:
        radial-gradient(
            circle at top,
            #2a2140 0%,
            #111118 38%,
            #09090d 100%
        );

    color: white;

    font-family:
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;
}

.page {
    max-width: 620px;
    margin: 0 auto;
}

h1 {
    margin: 4px 0 2px;

    font-size: 30px;
    letter-spacing: -1px;
}

.subtitle {
    opacity: 0.65;
    margin-bottom: 18px;
}

.card {
    background:
        rgba(
            255,
            255,
            255,
            0.07
        );

    border:
        1px solid
        rgba(
            255,
            255,
            255,
            0.10
        );

    border-radius: 18px;

    padding: 16px;

    margin-bottom: 14px;

    backdrop-filter:
        blur(10px);
}

.card h2 {
    margin: 0 0 12px;

    font-size: 18px;
}

.now-row {
    display: flex;

    align-items: center;

    gap: 10px;
}

.now-playing {
    flex: 1;

    font-size: 21px;

    font-weight: 700;

    overflow-wrap: anywhere;
}

.favorite-main {
    width: 48px;
    min-width: 48px;

    font-size: 24px;

    padding: 0;
}

.small {
    opacity: 0.65;

    font-size: 13px;

    margin-top: 4px;
}

.mode {
    margin-top: 10px;

    font-size: 14px;

    opacity: 0.7;
}

.tag-line {
    margin-top: 7px;

    font-size: 13px;

    opacity: 0.75;

    overflow-wrap: anywhere;
}

.grid {
    display: grid;

    grid-template-columns:
        repeat(
            2,
            minmax(
                0,
                1fr
            )
        );

    gap: 9px;
}

.grid3 {
    display: grid;

    grid-template-columns:
        repeat(
            3,
            minmax(
                0,
                1fr
            )
        );

    gap: 9px;
}

button {
    border: 0;

    border-radius: 13px;

    min-height: 48px;

    padding: 10px 12px;

    background: #343442;

    color: white;

    font-size: 15px;

    font-weight: 650;

    touch-action: manipulation;
}

button:active {
    transform: scale(0.97);
}

button.active {
    background: #7063d7;
}

button.big {
    min-height: 58px;

    font-size: 17px;
}

button.warning {
    background: #663640;
}

.slider-row {
    margin: 14px 0;
}

.slider-header {
    display: flex;

    justify-content: space-between;

    margin-bottom: 7px;

    font-size: 14px;
}

.value {
    opacity: 0.65;

    font-variant-numeric:
        tabular-nums;
}

input[type="range"] {
    width: 100%;

    height: 34px;
}

.status-dot {
    display: inline-block;

    width: 9px;
    height: 9px;

    border-radius: 50%;

    margin-right: 5px;

    background: #5dd77c;
}


/* ========================================================= */
/* FILTERS                                                   */
/* ========================================================= */

.filters {
    display: flex;

    gap: 7px;

    overflow-x: auto;

    padding: 2px 0 12px;

    scrollbar-width: none;
}

.filters::-webkit-scrollbar {
    display: none;
}

.filter-chip {
    flex: 0 0 auto;

    min-height: 38px;

    border-radius: 999px;

    padding: 7px 13px;

    font-size: 13px;

    background: #2d2d38;
}

.filter-chip.active {
    background: #7063d7;
}


/* ========================================================= */
/* GALLERY                                                   */
/* ========================================================= */

.gallery-header {
    display: flex;

    align-items: center;

    justify-content: space-between;

    margin-bottom: 10px;
}

.gallery-header h2 {
    margin: 0;
}

.gallery-count {
    font-size: 13px;

    opacity: 0.55;
}

.gallery {
    display: grid;

    grid-template-columns:
        repeat(
            3,
            minmax(
                0,
                1fr
            )
        );

    gap: 7px;
}

.gallery-item {
    position: relative;

    overflow: hidden;

    padding: 0;

    margin: 0;

    width: 100%;

    aspect-ratio: 1 / 1;

    min-height: 0;

    border-radius: 11px;

    background: #202029;

    border:
        2px solid
        transparent;
}

.gallery-item.selected {
    border-color: #8b7cff;

    box-shadow:
        0 0 0 2px
        rgba(
            139,
            124,
            255,
            0.25
        );
}

.gallery-image {
    width: 100%;
    height: 100%;

    display: block;

    object-fit: cover;

    image-rendering: pixelated;

    background: black;
}

.gallery-label {
    position: absolute;

    left: 0;
    right: 0;
    bottom: 0;

    padding:
        18px 5px 5px;

    background:
        linear-gradient(
            transparent,
            rgba(
                0,
                0,
                0,
                0.88
            )
        );

    font-size: 10px;

    line-height: 1.15;

    text-align: left;

    white-space: nowrap;

    overflow: hidden;

    text-overflow: ellipsis;
}

.gallery-star {
    position: absolute;

    top: 4px;
    right: 4px;

    width: 28px;
    height: 28px;

    min-height: 0;

    padding: 0;

    border-radius: 50%;

    background:
        rgba(
            0,
            0,
            0,
            0.66
        );

    font-size: 16px;

    z-index: 2;
}

.gallery-index {
    position: absolute;

    top: 5px;
    left: 5px;

    padding: 2px 5px;

    border-radius: 7px;

    background:
        rgba(
            0,
            0,
            0,
            0.58
        );

    font-size: 9px;
}

.empty-gallery {
    grid-column: 1 / -1;

    padding: 24px 10px;

    text-align: center;

    opacity: 0.55;
}

.footer {
    text-align: center;

    opacity: 0.45;

    padding: 12px;

    font-size: 12px;
}

@media (
    min-width: 520px
) {

    .gallery {
        grid-template-columns:
            repeat(
                4,
                minmax(
                    0,
                    1fr
                )
            );
    }

}

</style>

</head>


<body>

<div class="page">


<h1>
    Festival Totem
</h1>


<div class="subtitle">

    <span class="status-dot"></span>

    Live controller

</div>


<!-- ===================================================== -->
<!-- NOW PLAYING                                           -->
<!-- ===================================================== -->

<div class="card">

    <h2>
        Now Playing
    </h2>


    <div class="now-row">

        <div
            class="now-playing"
            id="nowPlaying"
        >
            Connecting...
        </div>


        <button
            class="favorite-main"
            id="favoriteButton"
            onclick="send('toggle_favorite')"
        >
            ☆
        </button>

    </div>


    <div
        class="small"
        id="imageInfo"
    ></div>


    <div
        class="mode"
        id="modeInfo"
    ></div>


    <div
        class="tag-line"
        id="tagInfo"
    ></div>


    <button
        style="
            width: 100%;
            margin-top: 10px;
        "
        onclick="editTags()"
    >
        Edit Tags
    </button>

</div>


<!-- ===================================================== -->
<!-- EFFECTS                                               -->
<!-- ===================================================== -->

<div class="card">

    <h2>
        Effects
    </h2>


    <div class="grid3">

        <button
            data-effect="Rainbow"
            onclick="setEffect('Rainbow')"
        >
            Rainbow
        </button>

        <button
            data-effect="Waves"
            onclick="setEffect('Waves')"
        >
            Waves
        </button>

        <button
            data-effect="Plasma"
            onclick="setEffect('Plasma')"
        >
            Plasma
        </button>

        <button
            data-effect="Stars"
            onclick="setEffect('Stars')"
        >
            Stars
        </button>

        <button
            data-effect="Text"
            onclick="setEffect('Text')"
        >
            Text
        </button>

        <button
            data-effect="Party"
            onclick="setEffect('Party')"
        >
            Party
        </button>

        <button
            data-effect="Image"
            onclick="setEffect('Image')"
        >
            Images
        </button>

    </div>

</div>


<!-- ===================================================== -->
<!-- LIBRARY                                               -->
<!-- ===================================================== -->

<div class="card">

    <div class="gallery-header">

        <h2>
            Library
        </h2>


        <div
            class="gallery-count"
            id="galleryCount"
        >
            0 items
        </div>

    </div>


    <div
        class="filters"
        id="filters"
    ></div>


    <div
        class="gallery"
        id="gallery"
    ></div>

</div>


<!-- ===================================================== -->
<!-- MASTER                                                -->
<!-- ===================================================== -->

<div class="card">

    <h2>
        Master
    </h2>


    <div class="slider-row">

        <div class="slider-header">

            <span>
                Brightness
            </span>

            <span
                class="value"
                id="brightnessValue"
            >
                --
            </span>

        </div>


        <input
            id="brightness"

            type="range"

            min="0.10"
            max="1.00"
            step="0.05"

            oninput="
                showPercent(
                    'brightnessValue',
                    this.value
                );

                sendRange(
                    'brightness',
                    this.value
                );
            "
        >

    </div>


    <div class="slider-row">

        <div class="slider-header">

            <span>
                Speed
            </span>

            <span
                class="value"
                id="speedValue"
            >
                --
            </span>

        </div>


        <input
            id="speed"

            type="range"

            min="0.10"
            max="5.00"
            step="0.10"

            oninput="
                showNumber(
                    'speedValue',
                    this.value,
                    'x'
                );

                sendRange(
                    'speed',
                    this.value
                );
            "
        >

    </div>


    <div class="grid">

        <button
            class="big"

            id="pauseButton"

            onclick="
                send(
                    'toggle_pause'
                )
            "
        >
            Pause
        </button>


        <button
            class="big"

            onclick="
                send(
                    'reload_library'
                )
            "
        >
            Reload Library
        </button>

    </div>

</div>


<!-- ===================================================== -->
<!-- NAVIGATION                                            -->
<!-- ===================================================== -->

<div class="card">

    <h2>
        Image Navigation
    </h2>


    <div class="grid">

        <button
            class="big"

            onclick="
                send(
                    'image_prev'
                )
            "
        >
            ◀ Previous
        </button>


        <button
            class="big"

            onclick="
                send(
                    'image_next'
                )
            "
        >
            Next ▶
        </button>

    </div>


    <div
        class="grid"
        style="margin-top: 9px;"
    >

        <button
            onclick="
                send(
                    'mode_prev'
                )
            "
        >
            ◀ Mode
        </button>


        <button
            onclick="
                send(
                    'mode_next'
                )
            "
        >
            Mode ▶
        </button>

    </div>

</div>


<!-- ===================================================== -->
<!-- FRAMING                                               -->
<!-- ===================================================== -->

<div class="card">

    <h2>
        Image Framing
    </h2>


    <div class="slider-row">

        <div class="slider-header">

            <span>
                Zoom
            </span>

            <span
                class="value"
                id="zoomValue"
            >
                --
            </span>

        </div>


        <input
            id="zoom"

            type="range"

            min="1.00"
            max="5.00"
            step="0.05"

            oninput="
                showNumber(
                    'zoomValue',
                    this.value,
                    'x'
                );

                sendRange(
                    'zoom',
                    this.value
                );
            "
        >

    </div>


    <div class="slider-row">

        <div class="slider-header">

            <span>
                Crop Left / Right
            </span>

            <span
                class="value"
                id="cropXValue"
            >
                --
            </span>

        </div>


        <input
            id="cropX"

            type="range"

            min="0.00"
            max="1.00"
            step="0.01"

            oninput="
                showPercent(
                    'cropXValue',
                    this.value
                );

                sendRange(
                    'crop_x',
                    this.value
                );
            "
        >

    </div>


    <div class="slider-row">

        <div class="slider-header">

            <span>
                Crop Up / Down
            </span>

            <span
                class="value"
                id="cropYValue"
            >
                --
            </span>

        </div>


        <input
            id="cropY"

            type="range"

            min="0.00"
            max="1.00"
            step="0.01"

            oninput="
                showPercent(
                    'cropYValue',
                    this.value
                );

                sendRange(
                    'crop_y',
                    this.value
                );
            "
        >

    </div>

</div>


<!-- ===================================================== -->
<!-- PROCESSING                                            -->
<!-- ===================================================== -->

<div class="card">

    <h2>
        Image Processing
    </h2>


    <div class="slider-row">

        <div class="slider-header">

            <span>
                Contrast
            </span>

            <span
                class="value"
                id="contrastValue"
            >
                --
            </span>

        </div>


        <input
            id="contrast"

            type="range"

            min="0.25"
            max="3.00"
            step="0.05"

            oninput="
                showNumber(
                    'contrastValue',
                    this.value,
                    ''
                );

                sendRange(
                    'contrast',
                    this.value
                );
            "
        >

    </div>


    <div class="slider-row">

        <div class="slider-header">

            <span>
                Saturation
            </span>

            <span
                class="value"
                id="saturationValue"
            >
                --
            </span>

        </div>


        <input
            id="saturation"

            type="range"

            min="0.00"
            max="3.00"
            step="0.05"

            oninput="
                showNumber(
                    'saturationValue',
                    this.value,
                    ''
                );

                sendRange(
                    'saturation',
                    this.value
                );
            "
        >

    </div>


    <div class="slider-row">

        <div class="slider-header">

            <span>
                Gamma
            </span>

            <span
                class="value"
                id="gammaValue"
            >
                --
            </span>

        </div>


        <input
            id="gamma"

            type="range"

            min="0.25"
            max="3.00"
            step="0.05"

            oninput="
                showNumber(
                    'gammaValue',
                    this.value,
                    ''
                );

                sendRange(
                    'gamma',
                    this.value
                );
            "
        >

    </div>


    <div class="grid">

        <button
            id="sharpenButton"

            onclick="
                send(
                    'toggle_sharpen'
                )
            "
        >
            Sharpen
        </button>


        <button
            id="ditherButton"

            onclick="
                send(
                    'toggle_dither'
                )
            "
        >
            Dither
        </button>

    </div>


    <button
        class="warning"

        style="
            width: 100%;
            margin-top: 10px;
        "

        onclick="
            if (
                confirm(
                    'Reset settings for this image?'
                )
            ) {
                send(
                    'reset_image'
                );
            }
        "
    >
        Reset Current Image
    </button>

</div>


<div class="footer">
    Phone → Mac Simulator → Festival Totem
</div>


</div>


<script>


let currentState = {};

let activeFilter = "All";

let gallerySignature = "";

let filterSignature = "";

const timers = {};


// ===========================================================
// COMMANDS
// ===========================================================

async function command(
    commandName,
    value = null
) {

    try {

        await fetch(
            "/api/command",
            {
                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify(
                    {
                        command:
                            commandName,

                        value:
                            value
                    }
                )
            }
        );

    } catch (error) {

        console.log(
            "Command error:",
            error
        );

    }

}


function send(
    commandName
) {

    command(
        commandName
    );

}


function setEffect(
    effectName
) {

    command(
        "effect",
        effectName
    );

}


function selectImage(
    index
) {

    command(
        "select_image",
        index
    );

}


// ===========================================================
// TAG EDITOR
// ===========================================================

function editTags() {

    if (
        !currentState.image_name
    ) {

        return;

    }


    const currentTags =
        currentState.image_tags
        || [];


    const answer =
        prompt(
            "Enter tags separated by commas:",
            currentTags.join(", ")
        );


    if (
        answer === null
    ) {

        return;

    }


    const tags =
        answer
        .split(",")
        .map(
            function(tag) {

                return tag.trim();

            }
        )
        .filter(
            function(tag) {

                return tag.length > 0;

            }
        );


    command(
        "set_tags",
        tags
    );

}


// ===========================================================
// RANGE COMMANDS
// ===========================================================

function sendRange(
    name,
    value
) {

    clearTimeout(
        timers[name]
    );


    timers[name] =
        setTimeout(
            function() {

                command(
                    name,
                    parseFloat(
                        value
                    )
                );

            },
            80
        );

}


// ===========================================================
// LABEL HELPERS
// ===========================================================

function showPercent(
    id,
    value
) {

    document
        .getElementById(
            id
        )
        .textContent =
            Math.round(
                parseFloat(
                    value
                ) * 100
            )
            + "%";

}


function showNumber(
    id,
    value,
    suffix
) {

    document
        .getElementById(
            id
        )
        .textContent =
            parseFloat(
                value
            )
            .toFixed(
                2
            )
            + suffix;

}


function syncRange(
    id,
    value
) {

    const element =
        document.getElementById(
            id
        );


    if (
        document.activeElement
        !== element
    ) {

        element.value =
            value;

    }

}


// ===========================================================
// FILTERS
// ===========================================================

function getAllTags(
    library
) {

    const tags =
        new Set();


    library.forEach(
        function(item) {

            (
                item.tags || []
            )
            .forEach(
                function(tag) {

                    tags.add(
                        tag
                    );

                }
            );

        }
    );


    return Array.from(
        tags
    ).sort(
        function(a, b) {

            return a.localeCompare(
                b
            );

        }
    );

}


function renderFilters(
    library
) {

    const tags =
        getAllTags(
            library
        );


    const filters = [
        "All",
        "Favorites",
        ...tags
    ];


    const signature =
        JSON.stringify(
            filters
        );


    if (
        signature ===
        filterSignature
    ) {

        updateFilterSelection();

        return;

    }


    filterSignature =
        signature;


    const container =
        document.getElementById(
            "filters"
        );


    container.innerHTML =
        "";


    filters.forEach(
        function(filterName) {

            const button =
                document.createElement(
                    "button"
                );


            button.className =
                "filter-chip";


            button.dataset.filter =
                filterName;


            button.textContent =
                filterName;


            button.onclick =
                function() {

                    activeFilter =
                        filterName;

                    gallerySignature =
                        "";

                    updateFilterSelection();

                    renderGallery(
                        currentState.library
                        || []
                    );

                };


            container.appendChild(
                button
            );

        }
    );


    updateFilterSelection();

}


function updateFilterSelection() {

    document
        .querySelectorAll(
            ".filter-chip"
        )
        .forEach(
            function(button) {

                button.classList.toggle(
                    "active",

                    button.dataset.filter
                    === activeFilter
                );

            }
        );

}


function filteredLibrary(
    library
) {

    if (
        activeFilter === "All"
    ) {

        return library;

    }


    if (
        activeFilter ===
        "Favorites"
    ) {

        return library.filter(
            function(item) {

                return item.favorite;

            }
        );

    }


    return library.filter(
        function(item) {

            return (
                item.tags
                || []
            ).includes(
                activeFilter
            );

        }
    );

}


// ===========================================================
// GALLERY
// ===========================================================

function renderGallery(
    library
) {

    const visible =
        filteredLibrary(
            library
        );


    const signature =
        JSON.stringify(
            {
                filter:
                    activeFilter,

                items:
                    visible.map(
                        function(item) {

                            return [
                                item.index,
                                item.name,
                                item.favorite,
                                item.tags
                            ];

                        }
                    )
            }
        );


    if (
        signature ===
        gallerySignature
    ) {

        updateGallerySelection(
            currentState
            .current_image_index
        );

        return;

    }


    gallerySignature =
        signature;


    const gallery =
        document.getElementById(
            "gallery"
        );


    gallery.innerHTML =
        "";


    if (
        visible.length === 0
    ) {

        const empty =
            document.createElement(
                "div"
            );


        empty.className =
            "empty-gallery";


        empty.textContent =
            "Nothing in this filter yet.";


        gallery.appendChild(
            empty
        );

    }


    visible.forEach(
        function(item) {

            const tile =
                document.createElement(
                    "button"
                );


            tile.className =
                "gallery-item";


            tile.dataset.index =
                item.index;


            tile.onclick =
                function() {

                    selectImage(
                        item.index
                    );

                };


            const image =
                document.createElement(
                    "img"
                );


            image.className =
                "gallery-image";


            image.src =
                "/thumb/"
                + item.index;


            image.alt =
                item.name;


            const indexLabel =
                document.createElement(
                    "div"
                );


            indexLabel.className =
                "gallery-index";


            indexLabel.textContent =
                item.index + 1;


            const star =
                document.createElement(
                    "button"
                );


            star.className =
                "gallery-star";


            star.textContent =
                item.favorite
                ? "★"
                : "☆";


            star.onclick =
                function(event) {

                    event.stopPropagation();


                    command(
                        "set_favorite_index",
                        {
                            index:
                                item.index,

                            favorite:
                                !item.favorite
                        }
                    );

                };


            const label =
                document.createElement(
                    "div"
                );


            label.className =
                "gallery-label";


            label.textContent =
                item.name;


            tile.appendChild(
                image
            );


            tile.appendChild(
                indexLabel
            );


            tile.appendChild(
                star
            );


            tile.appendChild(
                label
            );


            gallery.appendChild(
                tile
            );

        }
    );


    document
        .getElementById(
            "galleryCount"
        )
        .textContent =
            visible.length
            + " / "
            + library.length;

}


function updateGallerySelection(
    currentIndex
) {

    document
        .querySelectorAll(
            ".gallery-item"
        )
        .forEach(
            function(item) {

                const itemIndex =
                    parseInt(
                        item.dataset.index
                    );


                item.classList.toggle(
                    "selected",

                    itemIndex ===
                    currentIndex
                );

            }
        );

}


// ===========================================================
// STATE UPDATE
// ===========================================================

async function updateState() {

    try {

        const response =
            await fetch(
                "/api/state",
                {
                    cache:
                        "no-store"
                }
            );


        const state =
            await response.json();


        currentState =
            state;


        document
            .getElementById(
                "nowPlaying"
            )
            .textContent =
                state.effect
                || "Unknown";


        if (
            state.image_name
        ) {

            document
                .getElementById(
                    "imageInfo"
                )
                .textContent =
                    state.image_index
                    + " / "
                    + state.image_count
                    + " • "
                    + state.image_name;

        } else {

            document
                .getElementById(
                    "imageInfo"
                )
                .textContent =
                    "No image selected";

        }


        document
            .getElementById(
                "modeInfo"
            )
            .textContent =
                state.image_mode
                ? (
                    "Mode: "
                    + state.image_mode
                )
                : "";


        const tags =
            state.image_tags
            || [];


        document
            .getElementById(
                "tagInfo"
            )
            .textContent =
                tags.length
                ? (
                    "Tags: "
                    + tags.join(
                        " • "
                    )
                )
                : "No tags yet";


        const favoriteButton =
            document.getElementById(
                "favoriteButton"
            );


        favoriteButton.textContent =
            state.image_favorite
            ? "★"
            : "☆";


        favoriteButton.classList.toggle(
            "active",
            state.image_favorite
        );


        document
            .querySelectorAll(
                "[data-effect]"
            )
            .forEach(
                function(button) {

                    button.classList.toggle(
                        "active",

                        button.dataset.effect
                        === state.effect
                    );

                }
            );


        if (
            state.library
        ) {

            renderFilters(
                state.library
            );


            renderGallery(
                state.library
            );


            updateGallerySelection(
                state.current_image_index
            );

        }


        syncRange(
            "brightness",
            state.brightness
        );


        showPercent(
            "brightnessValue",
            state.brightness
        );


        syncRange(
            "speed",
            state.speed
        );


        showNumber(
            "speedValue",
            state.speed,
            "x"
        );


        const pauseButton =
            document.getElementById(
                "pauseButton"
            );


        pauseButton.textContent =
            state.paused
            ? "Resume"
            : "Pause";


        pauseButton.classList.toggle(
            "active",
            state.paused
        );


        if (
            state.image_settings
        ) {

            const settings =
                state.image_settings;


            syncRange(
                "zoom",
                settings.zoom
            );


            showNumber(
                "zoomValue",
                settings.zoom,
                "x"
            );


            syncRange(
                "cropX",
                settings.crop_x
            );


            showPercent(
                "cropXValue",
                settings.crop_x
            );


            syncRange(
                "cropY",
                settings.crop_y
            );


            showPercent(
                "cropYValue",
                settings.crop_y
            );


            syncRange(
                "contrast",
                settings.contrast
            );


            showNumber(
                "contrastValue",
                settings.contrast,
                ""
            );


            syncRange(
                "saturation",
                settings.saturation
            );


            showNumber(
                "saturationValue",
                settings.saturation,
                ""
            );


            syncRange(
                "gamma",
                settings.gamma
            );


            showNumber(
                "gammaValue",
                settings.gamma,
                ""
            );


            document
                .getElementById(
                    "sharpenButton"
                )
                .classList.toggle(
                    "active",
                    settings.sharpen
                );


            document
                .getElementById(
                    "ditherButton"
                )
                .classList.toggle(
                    "active",
                    settings.dither
                );

        }

    } catch (error) {

        document
            .getElementById(
                "nowPlaying"
            )
            .textContent =
                "Disconnected";

    }

}


updateState();


setInterval(
    updateState,
    300
);


</script>

</body>

</html>
'''


# ============================================================
# PHONE CONTROL SERVER
# ============================================================

class PhoneControlServer:

    def __init__(
        self,
        port=8765,
    ):

        self.port = port

        self.commands = Queue()

        self.state_lock = (
            threading.Lock()
        )

        self.state = {}

        self.thumbnail_provider = None

        self.server = None

        self.thread = None


    def update_state(
        self,
        state,
    ):

        with self.state_lock:

            self.state = dict(
                state
            )


    def get_state(
        self,
    ):

        with self.state_lock:

            return dict(
                self.state
            )


    def set_thumbnail_provider(
        self,
        provider,
    ):

        self.thumbnail_provider = (
            provider
        )


    def add_command(
        self,
        command,
        value=None,
    ):

        self.commands.put(
            {
                "command":
                    command,

                "value":
                    value,
            }
        )


    def get_commands(
        self,
    ):

        result = []

        while True:

            try:

                result.append(
                    self.commands
                    .get_nowait()
                )

            except Empty:

                break

        return result


    def get_local_ip(
        self,
    ):

        sock = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM,
        )

        try:

            sock.connect(
                (
                    "8.8.8.8",
                    80,
                )
            )

            address = (
                sock
                .getsockname()[0]
            )

        except Exception:

            try:

                address = (
                    socket
                    .gethostbyname(
                        socket
                        .gethostname()
                    )
                )

            except Exception:

                address = (
                    "127.0.0.1"
                )

        finally:

            sock.close()

        return address


    def start(
        self,
    ):

        control_server = self


        class Handler(
            BaseHTTPRequestHandler
        ):

            def log_message(
                self,
                format,
                *args,
            ):

                return


            def send_bytes(
                self,
                data,
                content_type,
                status=200,
            ):

                self.send_response(
                    status
                )

                self.send_header(
                    "Content-Type",
                    content_type,
                )

                self.send_header(
                    "Content-Length",
                    str(
                        len(data)
                    ),
                )

                self.send_header(
                    "Cache-Control",
                    "no-store",
                )

                self.end_headers()

                self.wfile.write(
                    data
                )


            def do_GET(
                self,
            ):

                if (
                    self.path
                    == "/"
                ):

                    data = (
                        PHONE_HTML
                        .encode(
                            "utf-8"
                        )
                    )

                    self.send_bytes(
                        data,
                        (
                            "text/html; "
                            "charset=utf-8"
                        ),
                    )

                    return


                if (
                    self.path
                    == "/api/state"
                ):

                    state = (
                        control_server
                        .get_state()
                    )

                    data = (
                        json.dumps(
                            state
                        )
                        .encode(
                            "utf-8"
                        )
                    )

                    self.send_bytes(
                        data,
                        "application/json",
                    )

                    return


                if (
                    self.path.startswith(
                        "/thumb/"
                    )
                ):

                    try:

                        index_text = (
                            self.path
                            .split(
                                "?",
                                1
                            )[0]
                            .split("/")[-1]
                        )


                        index = int(
                            index_text
                        )


                        if (
                            control_server
                            .thumbnail_provider
                            is None
                        ):

                            raise RuntimeError(
                                "No thumbnail provider"
                            )


                        thumbnail = (
                            control_server
                            .thumbnail_provider(
                                index
                            )
                        )


                        if thumbnail is None:

                            raise RuntimeError(
                                "Thumbnail unavailable"
                            )


                        self.send_bytes(
                            thumbnail,
                            "image/jpeg",
                        )

                        return


                    except Exception:

                        self.send_bytes(
                            b"",
                            "image/jpeg",
                            404,
                        )

                        return


                self.send_bytes(
                    b"Not Found",
                    "text/plain",
                    404,
                )


            def do_POST(
                self,
            ):

                if (
                    self.path
                    != "/api/command"
                ):

                    self.send_bytes(
                        b"Not Found",
                        "text/plain",
                        404,
                    )

                    return


                try:

                    length = int(
                        self.headers.get(
                            "Content-Length",
                            "0",
                        )
                    )


                    raw = (
                        self.rfile.read(
                            length
                        )
                    )


                    payload = (
                        json.loads(
                            raw.decode(
                                "utf-8"
                            )
                        )
                    )


                    command = (
                        payload.get(
                            "command"
                        )
                    )


                    value = (
                        payload.get(
                            "value"
                        )
                    )


                    if command:

                        control_server.add_command(
                            command,
                            value,
                        )


                    self.send_bytes(
                        b'{"ok": true}',
                        "application/json",
                    )


                except Exception as error:

                    data = (
                        json.dumps(
                            {
                                "ok":
                                    False,

                                "error":
                                    str(error),
                            }
                        )
                        .encode(
                            "utf-8"
                        )
                    )


                    self.send_bytes(
                        data,
                        "application/json",
                        400,
                    )


        self.server = (
            ThreadingHTTPServer(
                (
                    "0.0.0.0",
                    self.port,
                ),
                Handler,
            )
        )


        self.thread = (
            threading.Thread(
                target=(
                    self.server
                    .serve_forever
                ),
                daemon=True,
            )
        )


        self.thread.start()


        address = (
            self.get_local_ip()
        )


        print()

        print(
            "========================================"
        )

        print(
            "PHONE CONTROLLER READY"
        )

        print(
            "========================================"
        )

        print(
            "Open on your phone:"
        )

        print(
            f"http://{address}:{self.port}"
        )

        print(
            "========================================"
        )

        print()


        return (
            f"http://{address}:{self.port}"
        )


    def stop(
        self,
    ):

        if self.server:

            self.server.shutdown()

            self.server.server_close()

            self.server = None
