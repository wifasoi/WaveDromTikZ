#!/usr/bin/env python

import re
import yaml
import argparse
import sys
import os.path

from math import ceil
from collections import namedtuple


STANDALONE_TEX_HEADER = r"""
\documentclass[crop,tikz]{standalone}
\usepackage{tikz}
\usepackage{ifthen}
\usepackage{listings}

\usetikzlibrary{ calc, positioning, decorations.markings, patterns}
% all other packages and stuff you need for the picture
%
\begin{document}
\begin{tikzpicture}[thick]
"""

STANDALONE_TEX_FOOTER = r"""
\end{tikzpicture}
\end{document}
"""

# A TikZ (LaTeX) header to be included before a waveform diagram. Defines
# various primitives for drawing parts of a waveform.
TIKZ_HEADER = r"""
% Seperation between lines
\pgfmathsetlengthmacro{\wavesep}{2.0em}

% Height of a waveform
\pgfmathsetlengthmacro{\waveheight}{1.2em}

% Width of a brick (half a cycle)
\pgfmathsetlengthmacro{\wavewidth}{1em}

% Width of the slant on slanted signal changes
\pgfmathsetlengthmacro{\transitionwidth}{0.3em}

% Width of the curve on slow signal changes (e.g. to z)
\pgfmathsetlengthmacro{\curvedtransitionwidth}{1.0em}

% Special signal styles
\tikzset{wave x/.style={pattern=north east lines}}
\tikzset{wave bus/.style={fill=white}}
\tikzset{wave busyellow/.style={fill=yellow!25!white}}
\tikzset{wave busorange/.style={fill=orange!25!white}}
\tikzset{wave busblue/.style={fill=blue!25!white}}
\tikzset{wave pulled/.style={dotted}}

% Initialise pointer
\coordinate (last waveform);

% Label for a signal. Arguments:
%  #1: The human-readable label string
\newcommand{\signallabel}[1]{
   \node [ anchor=east
         , left=0 of last waveform
         , minimum height=\waveheight
         ]
         {#1};
}

% Advance the "last brick" coordinate to the next position
%  #1: Width of a brick
\newcommand{\advancebrick}[1]{
   \coordinate (last brick) at ([shift={(#1*\wavewidth,0)}]last brick);
}

% Add the label for a bus
%  #1: Label coordinate
%  #2: Label text
\newcommand{\busdata}[2]{
   \node [ inner sep=0
         , minimum height=\waveheight
         , anchor=mid
         , font=\footnotesize
         ]
         at ([shift={(0.5*\transitionwidth,0)}]#1)
         {#2};
}

% Define a clip which will truncate a waveform at the left-hand side
%  #1: Width of a brick
%  #2: Truncation offset (in bricks)
%  #3: Number of bricks in waveform
\newcommand{\truncatewaveform}[3]{
   \coordinate (last brick) at ([shift={(-#2*\wavewidth,0)}]last brick);
   \clip ([shift={(#2*\wavewidth, 0.6*\waveheight)}]last brick)
         rectangle ++(#3*#1*\wavewidth-#2*\wavewidth,-1.2*\waveheight);
}

% Spacer Brick Overlay
%  #1: brick width
\newcommand{\brickspaceroverly}[1]{
   \pgfmathsetlengthmacro{\spacerheight}{1.2*\waveheight}
   \pgfmathsetlengthmacro{\spacerwidth}{\transitionwidth}
   \pgfmathsetlengthmacro{\spacergap}{0.7*\transitionwidth}

   % Mask off the waveform
   \fill [fill=white]
         ([xshift=-#1*\wavewidth-0.5*\spacergap-0.5*\spacerwidth, yshift=-0.5*\spacerheight]last brick)
      .. controls +(0.8*\spacergap, 0) and +(-0.8*\spacergap, 0)
      .. ++(\spacerwidth, \spacerheight)
      -- ++(\spacergap,0)
      .. controls +(-0.8*\spacergap, 0) and +(0.8*\spacergap, 0)
      .. ++(-\spacerwidth, -\spacerheight)
       ;

   % Lines
   \draw ([xshift=-#1*\wavewidth-0.5*\spacergap-0.5*\spacerwidth, yshift=-0.5*\spacerheight]last brick)
      .. controls +(0.8*\spacergap, 0) and +(-0.8*\spacergap, 0)
      .. ++(\spacerwidth, \spacerheight)
         ++(\spacergap,0)
      .. controls +(-0.8*\spacergap, 0) and +(0.8*\spacergap, 0)
      .. ++(-\spacerwidth, -\spacerheight)
       ;

}

% Generic mid-bus brick
%  #1: brick width
%  #2: brick style
\newcommand{\brickbus}[2]{
   \fill [#2]
         ([yshift= 0.5*\waveheight]last brick)
      -- ++(#1*\wavewidth,0)
      -- ++(0,-\waveheight)
      -- ++(-#1*\wavewidth,0)
      -- cycle
       ;
   \draw ([yshift= 0.5*\waveheight]last brick) -- ++(#1*\wavewidth,0)
         ([yshift=-0.5*\waveheight]last brick) -- ++(#1*\wavewidth,0)
       ;

   \advancebrick{#1}
}

% Generic mid-bit brick
%  #1: brick width
%  #2: Line style
%  #3: Start line offset (from bottom)
%  #4: End line offset (from bottom)
%  #5: Add arrow on transition
\newcommand{\brickbit}[5]{
   \pgfmathsetlengthmacro{\vstart}{(#3-0.5)*\waveheight}
   \pgfmathsetlengthmacro{\vend}{(#4-0.5)*\waveheight}

   % The bit value
   \draw [#2]
         ([yshift=\vend]last brick)
      |- ([yshift=\vstart, xshift=#1*\wavewidth]last brick);

   % Arrow (if required)
   \ifthenelse{\equal{#5}{1}}{
      \path [decoration={ markings
                        , mark=at position 0.5 with {\arrow{>}}
                        }
            , postaction={decorate}
            ]
            ([yshift=\vend]last brick)
         -- ([yshift=\vstart]last brick);
   }{}

   \advancebrick{#1}
}

% Generic bit-glitch brick
%  #1: brick width
%  #2: Style
%  #3: Edge start (offset from bottom)
\newcommand{\brickbitglitch}[3]{
   \pgfmathsetlengthmacro{\voffset}{(#3-0.5)*\waveheight}

   \draw [#2]
         ([yshift=\voffset]last brick)
      -- ([xshift=0.5*\transitionwidth]last brick)
      -- ([yshift=\voffset, xshift=\transitionwidth]last brick)
      -- ++(#1*\wavewidth - \transitionwidth,0);

   \advancebrick{#1}
}

% Generic sharp bit-to-bit transition
%  #1: brick width
%  #2: Brick style
%  #3: Old bit (offset from bottom)
%  #4: New bit (offset from bottom)
%  #5: Include arrow
\newcommand{\bricksharpbittobit}[5]{
   \pgfmathsetlengthmacro{\vstart}{(#3-0.5)*\waveheight}
   \pgfmathsetlengthmacro{\vend}{(#4-0.5)*\waveheight}

   % The transition and new bit
   \draw [#2]
         ([yshift=\vstart]last brick)
      -- ([yshift=\vend]last brick)
      -- ++(#1*\wavewidth,0);

   % Arrow (if required)
   \ifthenelse{\equal{#5}{1}}{
      \ifthenelse{\not\equal{#3}{#4}}{
         \path [decoration={ markings
                           , mark=at position 0.5 with {\arrow{>}}
                           }
               , postaction={decorate}
               ]
               ([yshift=\vstart]last brick)
            -- ([yshift=\vend]last brick);
      }{}
   }{}

   \advancebrick{#1}
}

% Generic sharp bus-to-bit transition
%  #1: brick width
%  #2: Brick style
%  #3: New bit (offset from bottom)
%  #4: Include arrow
\newcommand{\bricksharpbustobit}[4]{
   \pgfmathsetlengthmacro{\vstart}{((1-#3)-0.5)*\waveheight}
   \pgfmathsetlengthmacro{\vend}{(#3-0.5)*\waveheight}

   % The transition and new bit
   \draw [#2]
         ([yshift=\vstart]last brick)
      -- ([yshift=\vend]last brick)
      -- ++(#1*\wavewidth,0);

   % Arrow (if required)
   \ifthenelse{\equal{#4}{1}}{
      \path [decoration={ markings
                        , mark=at position 0.5 with {\arrow{>}}
                        }
            , postaction={decorate}
            ]
            ([yshift=\vstart]last brick)
         -- ([yshift=\vend]last brick);
   }{}

   \advancebrick{#1}
}

% Generic soft bit-to-bit transition
%  #1: brick width
%  #2: Last brick style
%  #3: This brick style
%  #4: Last bit (offset from bottom)
%  #5: New bit (offset from bottom)
\newcommand{\bricksmoothbittobit}[5]{
   \pgfmathsetlengthmacro{\vstart}{(#4-0.5)*\waveheight}
   \pgfmathsetlengthmacro{\vend}{(#5-0.5)*\waveheight}

   % Scale the transition depending on the magnitude of the level change
   \pgfmathsetlengthmacro{\thistranswidth}{abs(#4-#5)*\transitionwidth}
   \pgfmathsetlengthmacro{\thisleadwidth}{\transitionwidth - \thistranswidth}

   % The lead up to the transition
   \draw [#2]
         ([yshift=\vstart]last brick)
      -- ([yshift=\vstart, xshift=\thisleadwidth]last brick);

   % The transition itself
   \draw [#3]
         ([yshift=\vstart, xshift=\thisleadwidth]last brick)
      -- ([yshift=\vend, xshift=\transitionwidth]last brick)
      -- ++(#1*\wavewidth - \transitionwidth,0);

   \coordinate (last transition) at ([xshift=0.5*\transitionwidth]last brick);

   \advancebrick{#1}
}

% Generic curved bit-to-bit transition
%  #1: brick width
%  #2: Last brick style
%  #3: This brick style
%  #4: Last bit (offset from bottom)
%  #5: New bit (offset from bottom)
\newcommand{\brickcurvedbittobit}[5]{
   \pgfmathsetlengthmacro{\vstart}{(#4-0.5)*\waveheight}
   \pgfmathsetlengthmacro{\vend}{(#5-0.5)*\waveheight}

   % The curve itself
   \draw [#2]
         ([yshift=\vstart]last brick)
      .. controls ([yshift=\vstart]last brick)
              and ([yshift=\vend, xshift=0.2*\curvedtransitionwidth]last brick)
      .. ([yshift=\vend, xshift=\curvedtransitionwidth]last brick);

   % Start of the new bit
   \draw [#3]
         ([yshift=\vend, xshift=\curvedtransitionwidth]last brick)
      -- ++(#1*\wavewidth - \curvedtransitionwidth,0);

   \coordinate (last transition) at ([xshift=0.5*\curvedtransitionwidth]last brick);

   \advancebrick{#1}
}

% Generic soft transition from bit to bus
%  #1: brick width
%  #2: Bit style
%  #3: Bus style
%  #4: Bit (offset from bottom)
\newcommand{\bricksmoothbittobus}[4]{
   \pgfmathsetlengthmacro{\voffset}{(#4-0.5)*\waveheight}

   % Scale the transition depending on the magnitude of the level change
   \pgfmathsetlengthmacro{\thistranswidth}{(abs(#4-0.5)+0.5)*\transitionwidth}
   \pgfmathsetlengthmacro{\thisleadwidth}{\transitionwidth - \thistranswidth}

   % The lead up to the transition
   \draw [#2]
         ([yshift=\voffset]last brick)
      -- ([yshift=\voffset, xshift=\thisleadwidth]last brick);

   % Open-up the bus
   \draw [#3]
         ([xshift=#1*\wavewidth,    yshift= 0.5*\waveheight]last brick)
      -- ([xshift=\transitionwidth, yshift= 0.5*\waveheight]last brick)
      -- ([xshift=\thisleadwidth,   yshift=     \voffset]   last brick)
      -- ([xshift=\transitionwidth, yshift=-0.5*\waveheight]last brick)
      -- ([xshift=#1*\wavewidth,    yshift=-0.5*\waveheight]last brick)
      ;

   \coordinate (last transition) at ([xshift=0.5*\transitionwidth]last brick);

   \advancebrick{#1}
}

% Generic smooth transition from bus to bus
%  #1: brick width
%  #2: Bus style
%  #3: Bit style
\newcommand{\brickbustobus}[3]{

   % Close-down the old bus
   \draw [#2]
         ([yshift= 0.5*\waveheight]    last brick)
      -- ([xshift=0.5*\transitionwidth]last brick)
      -- ([yshift=-0.5*\waveheight]    last brick)
      ;

   % Open-up the new bus
   \draw [#3]
         ([xshift=#1*\wavewidth,    yshift= 0.5*\waveheight]last brick)
      -- ([xshift=\transitionwidth, yshift= 0.5*\waveheight]last brick)
      -- ([xshift=0.5*\transitionwidth]                     last brick)
      -- ([xshift=\transitionwidth, yshift=-0.5*\waveheight]last brick)
      -- ([xshift=#1*\wavewidth,    yshift=-0.5*\waveheight]last brick)
      ;

   \coordinate (last transition) at ([xshift=0.5*\transitionwidth]last brick);

   \advancebrick{#1}
}

% Generic smooth transition from bus to bit
%  #1: brick width
%  #2: Bus style
%  #3: Bit style
%  #4: Bit (offset from bottom)
\newcommand{\bricksmoothbustobit}[4]{
   \pgfmathsetlengthmacro{\voffset}{(#4-0.5)*\waveheight}

   % Scale the transition depending on the magnitude of the level change
   \pgfmathsetlengthmacro{\thistranswidth}{(abs(#4-0.5)+0.5)*\transitionwidth}
   \pgfmathsetlengthmacro{\thisleadwidth}{\transitionwidth - \thistranswidth}

   % Close-down the bus
   \draw [#2]
         ([                         yshift= 0.5*\waveheight]last brick)
      -- ([xshift=\thisleadwidth,   yshift= 0.5*\waveheight]last brick)
      -- ([xshift=\transitionwidth, yshift=     \voffset]   last brick)
      -- ([xshift=\thisleadwidth,   yshift=-0.5*\waveheight]last brick)
      -- ([                         yshift=-0.5*\waveheight]last brick)
      ;

   % The new bit
   \draw [#3]
         ([xshift=\transitionwidth, yshift=\voffset]last brick)
      -- ([xshift=#1*\wavewidth,    yshift=\voffset]last brick);

   \coordinate (last transition) at ([xshift=0.5*\transitionwidth]last brick);

   \advancebrick{#1}
}

% Generic curved transition from bus to bit
%  #1: brick width
%  #2: Bus style
%  #3: Bit style
%  #4: Bit (offset from bottom)
\newcommand{\brickcurvedbustobit}[4]{
   \pgfmathsetlengthmacro{\voffset}{(#4-0.5)*\waveheight}

   % Scale the transition depending on the magnitude of the level change
   \pgfmathsetlengthmacro{\thistranswidth}{(abs(#4-0.5)+0.5)*\transitionwidth}
   \pgfmathsetlengthmacro{\thisleadwidth}{\transitionwidth - \thistranswidth}

   % Close-down the bus
   \draw [#2]
         ([yshift= 0.5*\waveheight]last brick)
      .. controls ([                                   yshift= 0.5*\waveheight]last brick)
              and ([xshift=0.2*\curvedtransitionwidth, yshift=     \voffset]   last brick)
      .. ([xshift=\curvedtransitionwidth, yshift= \voffset]last brick)
      .. controls ([xshift=0.2*\curvedtransitionwidth, yshift=     \voffset]   last brick)
              and ([                                   yshift=-0.5*\waveheight]last brick)
      .. ([yshift=-0.5*\waveheight]last brick)
      ;

   % The new bit
   \draw [#3]
         ([xshift=\curvedtransitionwidth, yshift=\voffset]last brick)
      -- ([xshift=#1*\wavewidth,    yshift=\voffset]last brick);

   \coordinate (last transition) at ([xshift=0.5*\curvedtransitionwidth]last brick);

   \advancebrick{#1}
}
"""

WaveSection = namedtuple("WaveSection"
                        , [ "wave_type" # Either "bus", "bit"
                          , "glitch" # Glitch on continuations of same signal
                          , "bus_style" # TikZ styling for bus fill
                          , "bit_style" # TikZ styling for bit lines
                          , "bit_start_position" # Starting y-offset of bit waves
                          , "bit_end_position" # Ending y-offset of bit waves
                          , "bit_transition" # Either "sharp", "sharparrow", "smooth" or "curved"
                          ]
                        )

# Dictionary containing various WaveSection definitions for different types of
# waveform.
WAVES = {}

# High impedance
WAVES["z"] = WaveSection( wave_type          = "bit"
                        , glitch             = False
                        , bus_style          = None
                        , bit_style          = ""
                        , bit_start_position = 0.5
                        , bit_end_position   = 0.5
                        , bit_transition     = "curved"
                        )

# Logic levels
WAVES["logic"] = {}
for level in [0, 1]:
    WAVES["logic"][level] = WaveSection( wave_type          = "bit"
                                       , glitch             = True
                                       , bus_style          = None
                                       , bit_style          = ""
                                       , bit_start_position = level
                                       , bit_end_position   = level
                                       , bit_transition     = "smooth"
                                       )

# Pulled-Logic levels
WAVES["pulled"] = {}
for level in [0, 1]:
    WAVES["pulled"][level] = WaveSection( wave_type          = "bit"
                                        , glitch             = True
                                        , bus_style          = None
                                        , bit_style          = "wave pulled"
                                        , bit_start_position = level
                                        , bit_end_position   = level
                                        , bit_transition     = "curved"
                                        )

# Clock signals
WAVES["clk"] = {}
for clk_edge, first, second in [ (0, 0,0), (1, 1,1)
                                , ("posedge", 1,0), ("negedge", 0,1)
                                ]:
    WAVES["clk"][clk_edge] = {}
    for has_arrow in [False, True]:
       WAVES["clk"][clk_edge][has_arrow] \
          = WaveSection( wave_type          = "bit"
                       , glitch             = True
                       , bus_style          = None
                       , bit_style          = ""
                       , bit_start_position = first
                       , bit_end_position   = second
                       , bit_transition     = "sharparrow" if has_arrow else "sharp"
                       )

# Buses
WAVES["bus"] = {}
for name, style, glitch in [ ("x",      "wave x",         False)
                            , ("bus",    "wave bus",       True)
                            , ("yellow", "wave busyellow", True)
                            , ("orange", "wave busorange", True)
                            , ("blue",   "wave busblue",   True)
                            ]:
    WAVES["bus"][name] = WaveSection( wave_type          = "bus"
                                    , glitch             = glitch
                                    , bus_style          = style
                                    , bit_style          = None
                                    , bit_start_position = None
                                    , bit_end_position   = None
                                    , bit_transition     = "smooth"
                                    )


def get_brick(wave, odd_brick, brick_width):
    """
    Return a LaTeX string which inserts a brick of the type indicated by wave.
    """

    if wave.wave_type == "bus":
       # Just a bus of the given style
       return r"\brickbus{%f}{%s}"%(brick_width, wave.bus_style)
    elif wave.wave_type == "bit":
       # A bus with a given style.
       return r"\brickbit{%f}{%s}{%f}{%f}{%d}"%(
          brick_width,
          wave.bit_style,
          # Swap stard and end positions between odd and even bricks for clock
          # signals.
          wave.bit_end_position   if odd_brick else wave.bit_start_position,
          wave.bit_start_position if odd_brick else wave.bit_end_position,
          ( # Add an arrow to clock signals...
            wave.bit_start_position != wave.bit_end_position
            # ...on the leading edge...
            and not odd_brick
            # ...when an arrow is required.
            and wave.bit_transition == "sharparrow"
          )
       )


def get_transition_brick(last_wave, wave, brick_width):
    """
    Return a LaTeX string which inserts a transition brick from last_wave to wave.
    """

    if last_wave.wave_type == wave.wave_type == "bus":
       # Bus-to-bus
       if last_wave.glitch or last_wave.bus_style != wave.bus_style:
          # A gitch or a change
          return r"\brickbustobus{%f}{%s}{%s}"%( brick_width
                                               , last_wave.bus_style
                                               , wave.bus_style
                                               )
       else:
          # Bus is just a continuation of the last one
          return get_brick(wave, False, brick_width)
    elif last_wave.wave_type == wave.wave_type == "bit":
       # Bit-to-bit transition
       if last_wave.glitch and last_wave.bit_end_position == wave.bit_start_position:
          # A glitch
          if wave.bit_transition in ("sharp", "sharparrow"):
             # Sharp glitch, possibly with arrow
             return r"\bricksharpbittobit{%f}{%s}{%f}{%f}{%d}"%(
                brick_width,
                wave.bit_style,
                last_wave.bit_end_position,
                wave.bit_start_position,
                wave.bit_transition == "sharparrow",
             )
          else:
             # All other glitches
             return r"\brickbitglitch{%f}{%s}{%s}"%( brick_width
                                                   , wave.bit_style
                                                   , wave.bit_start_position
                                                   )
       elif last_wave.bit_end_position == wave.bit_start_position:
          # Same-level, no transition to make
          return get_brick(wave, False, brick_width)
       else:
          # Level changed
          if wave.bit_transition in ("sharp", "sharparrow"):
             # Sharp transition, possibly with arrow
             return r"\bricksharpbittobit{%f}{%s}{%f}{%f}{%d}"%(
                brick_width,
                wave.bit_style,
                last_wave.bit_end_position,
                wave.bit_start_position,
                wave.bit_transition == "sharparrow",
             )
          elif wave.bit_transition == "smooth":
             # Smooth transition
             return r"\bricksmoothbittobit{%f}{%s}{%s}{%f}{%f}"%(
                brick_width,
                last_wave.bit_style,
                wave.bit_style,
                last_wave.bit_end_position,
                wave.bit_start_position,
             )
          elif wave.bit_transition == "curved":
             # Curved transition
             return r"\brickcurvedbittobit{%f}{%s}{%s}{%f}{%f}"%(
                brick_width,
                last_wave.bit_style,
                wave.bit_style,
                last_wave.bit_end_position,
                wave.bit_start_position,
             )
          else:
             assert False, "Unknown bit_transition: %s"%(wave.bit_transition)
    elif last_wave.wave_type == "bit" and wave.wave_type == "bus":
       # Bit-to-bus transition
       return r"\bricksmoothbittobus{%f}{%s}{%s}{%f}"%(
          brick_width,
          last_wave.bit_style,
          wave.bus_style,
          last_wave.bit_end_position,
       )
    elif last_wave.wave_type == "bus" and wave.wave_type == "bit":
       # Bus-to-bit transition
       if wave.bit_transition in ("sharp", "sharparrow"):
          # Sharp transition, possibly with arrow
          return r"\bricksharpbustobit{%f}{%s}{%f}{%d}"%(
             brick_width,
             wave.bit_style,
             wave.bit_start_position,
             wave.bit_transition == "sharparrow"
          )
       elif wave.bit_transition == "smooth":
          # Smooth transition
          return r"\bricksmoothbustobit{%f}{%s}{%s}{%f}"%(
             brick_width,
             last_wave.bus_style,
             wave.bit_style,
             wave.bit_start_position,
          )
       elif wave.bit_transition == "curved":
          # Curved transition
          return r"\brickcurvedbustobit{%f}{%s}{%s}{%f}"%(
             brick_width,
             last_wave.bus_style,
             wave.bit_style,
             wave.bit_start_position,
          )
       else:
          assert False, "Unknown bit_transition: %s"%(wave.bit_transition)
    else:
       assert False, "Unknown wave types: %s and %s"%(last_wave.wave_type, wave.wave_type)


# Mapping from WaveDrom values to WaveSections
WAVEDROM_NAMES = {
    "z": WAVES["z"],
    "0": WAVES["logic"][0],
    "1": WAVES["logic"][1],
    "d": WAVES["pulled"][0],
    "u": WAVES["pulled"][1],
    "x": WAVES["bus"]["x"],
    "2": WAVES["bus"]["bus"],
    "=": WAVES["bus"]["bus"],
    "3": WAVES["bus"]["yellow"],
    "4": WAVES["bus"]["orange"],
    "5": WAVES["bus"]["blue"],
    "p": WAVES["clk"]["posedge"][False],
    "P": WAVES["clk"]["posedge"][True],
    "n": WAVES["clk"]["negedge"][False],
    "N": WAVES["clk"]["negedge"][True],
    "l": WAVES["clk"][0][False],
    "L": WAVES["clk"][0][True],
    "h": WAVES["clk"][1][False],
    "H": WAVES["clk"][1][True],
}


def render_waveform(signal_params):
    """
    Produce TikZ for just the waveform of a given signal.
    """
    wave   = signal_params.get("wave", "")
    node   = signal_params.get("node", "")
    data   = signal_params.get("data", [])
    phase  = signal_params.get("phase", 0.0)
    period = signal_params.get("period", 1.0)

    assert period >= 0.0, "Period must be positive or zero."

    # No waveform for empty description
    if wave == "":
       return ""

    # Pad node list
    node += "." * max(0, len(wave)-len(node))

    # Split up data in strings
    if isinstance(data) is str:
       data = data.split(" ")

    # Set up the 'last brick' pointer at the start of the waveform.
    out = [r"\coordinate (last brick) at (last waveform);"]

    # Start assuming the signal is x if not otherwise specified
    last_signal = "x" if wave[0] in ".|" else wave[0]

    # Draw the first part of the waveform to get the phase right
    if phase < 0.0:
       # -ve phase advances the waveform rightward
       out.append(r"\advancebrick{%f}"%(-phase*2.0))
    if phase > 0.0:
       # +ve phase advances the waveform leftward
       out.append(r"\truncatewaveform{%f}{%f}{%d}"%(period,phase*2.0,len(wave)*2))

    # Has the start of a bus been observed?
    bus_started = False
    bus_number  = 0

    # Draw the waveform, one timeslot at a time
    for time, (signal, node_name) in enumerate(zip(wave, node)):
       # Add a coordinate (which may be overwritten by a transition brick) to
       # indicate the current transition point
       out.append(r"\coordinate (last transition) at (last brick);")

       # Add coordinates for bus labels
       if signal not in '.|' and bus_started:
          out.append(r"\coordinate (bus %d) at ($(bus start)!0.5!(last brick)$);"%(
             bus_number
          ))
          bus_number += 1
          bus_started = False

       # Update a pointer to the start of every bus
       if signal in '=2345':
          # Add the label for the last bus

          out.append(r"\coordinate (bus start) at (last brick);")
          bus_started = True

       continued_signal = last_signal if signal in ".|" else signal
       # First half of the waveform/transition
       if time == 0 or signal in ".|":
          out.append(get_brick(WAVEDROM_NAMES[continued_signal], 0, period))
       else:
          out.append(get_transition_brick( WAVEDROM_NAMES[last_signal]
                                         , WAVEDROM_NAMES[continued_signal]
                                         , period
                                         ))

       # Second half of the waveform
       out.append(get_brick(WAVEDROM_NAMES[continued_signal], 1, period))

       # Record transition node positions
       if node_name != ".":
          out.append(r"\coordinate (%s) at (last transition);"%(node_name))

       # Draw the spacer spacer
       if signal == "|":
          out.append(r"\brickspaceroverly{%f}"%(period))

       last_signal = continued_signal

    # Add final bus label
    if bus_started:
       out.append(r"\coordinate (bus %d) at ($(bus start)!0.5!(last brick)$);"%(
          bus_number
       ))
       bus_number += 1
       bus_started = False

    # Add bus labels
    for i, datum in zip(range(bus_number), data):
       out.append(r"\busdata{bus %d}{%s};"%(i, datum))

    return "\n".join(out)


def render_signal(signal_params):
    """
    Produce a TikZ string defining the given waveform line with parameters as used
    by WaveDrom.
    """
    return r"""
       \signallabel{%s}
       %% A scope to ensure correct styling and limit the effect of clipping
       \begin{scope}[line cap=rect, line join=round]
          %s
       \end{scope}
       \coordinate (last waveform) at ([yshift=-\wavesep]last waveform);
    """%(
       signal_params.get("name", "").replace('_','\_'),
       render_waveform(signal_params)
    )


def render_help_lines(wavedrom):
    """
    Produce TikZ for a set of helplines on clock edges large enough to fill the
    space taken by the given WaveDrom.
    """
    width = max( (int(len(signal.get("wave","")) * signal.get("period", 1.0))
                       - int(signal.get("phase", 0.0)))
                 for signal in wavedrom["signal"]
               )

    height = len(wavedrom["signal"])

    return r"""
       \foreach \tick in {0,...,%d}{
          \draw [draw=black!75!white, dotted]
                ([xshift=\tick*2.0*\wavewidth,yshift=0.5*\waveheight]last waveform)
             -- ++(0, -%d*\wavesep + \wavesep - \waveheight);
       }
    """%(
       width, height
    )


def render_wavedrom(wavedrom):
    return r"%s%s%s"%( TIKZ_HEADER
                     , render_help_lines(wavedrom)
                     , "\n".join( render_signal(signal_params)
                                  for signal_params in wavedrom["signal"]
                                )
                     )

def print_header(args):
    print(TIKZ_HEADER)

def print_render_signal(args):
    print(render_signal(yaml.load(" ".join(args.signal))))

def print_render_wavedrom(args):

    with open(args.path, 'r') as input_file:
        wavedrom = render_wavedrom(yaml.load(input_file.read()))

        if args.standalone:
            wavedrom = "\n".join([STANDALONE_TEX_HEADER, wavedrom, STANDALONE_TEX_FOOTER])
        if args.output == sys.stdout:
            print(wavedrom)
        else:
            if os.path.isdir(args.output):
                args.output = os.path.join(args.output, os.path.splitext(os.path.basename(args.path))[0] + ".tikz")
                print(args.output)
            with open(args.output, 'w') as output_file:
                output_file.write(str(wavedrom))

if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers()

    header_parser = subparsers.add_parser('header')
    header_parser.set_defaults(func=print_header)

    signal_parser = subparsers.add_parser('signal')
    signal_parser.add_argument('signal', type=str, help='signal description')
    signal_parser.set_defaults(func=print_render_signal)

    wavedrom_parser = subparsers.add_parser('wavedrom')
    wavedrom_parser.add_argument('-o', '--output', default=sys.stdout, type=str, help='output TikZ file')
    wavedrom_parser.add_argument('-s', '--standalone', default=False, action='store_true', help='Create standalone tex file')
    wavedrom_parser.add_argument('path', type=str, help='input wavedrom file')
    wavedrom_parser.set_defaults(func=print_render_wavedrom)

    try:
       args = parser.parse_args()
       args.func(args)
    except (BrokenPipeError, IOError):
        pass
