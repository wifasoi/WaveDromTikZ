#!/usr/bin/env python

import re
import json

TIKZ_HEADER = r"""
% Height of a waveform
\pgfmathsetlengthmacro{\waveheight}{1em}

% Width of a brick (half a cycle)
\pgfmathsetlengthmacro{\wavewidth}{1em}

% Width of the slant on slanted signal changes
\pgfmathsetlengthmacro{\transitionwidth}{0.3em}

% Width of the curve on slow signal changes (e.g. to z)
\pgfmathsetlengthmacro{\slowtransitionwidth}{0.5em}

% Special signal styles
\tikzset{wave x/.style={pattern=north east lines}}
\tikzset{wave bus/.style={fill=white}}
\tikzset{wave busyellow/.style={fill=yellow}}
\tikzset{wave busorange/.style={fill=orange}}
\tikzset{wave busblue/.style={fill=blue}}
\tikzset{wave pulled/.style={dotted}}

% Label for a signal. Arguments:
%  #1: The human-readable label string
\newcommand{\signallabel}[1]{
	\node [ anchor=east
	      , left=0 of wave start
	      ]
	      {#1};
}

% Advance the "last brick" coordinate to the next position
%  #1: Width of a brick
\newcommand{\advancebrick}[1]{
	\coordinate (last brick) at ([shift={(#1*\wavewidth,0)}]last brick);
}

% Draw a brick truncated.
%  #1: Width of a brick
%  #2: Truncation offset (positive to truncate the front, negative off the back)
%  #3: The brick
\newcommand{\truncatebrick}[3]{
	\begin{scope}
		\coordinate (last brick) at ([shift={(-#2*\wavewidth,0)}]last brick);
		\clip ([shift={(#2*\wavewidth, 0.5*\waveheight)}]last brick)
		      rectangle ++(#1*\wavewidth-#2*\wavewidth,-\waveheight);
		#3
	\end{scope}
}

% Generic mid-bus brick
%  #1: 0 for odd, 1 for even half-ticks
%  #2: brick width
%  #3: fill style
\newcommand{\brickgenericbus}[3]{
	\fill [#3]
	      ([yshift= 0.5*\waveheight]last brick)
	   -- ++(#2*\wavewidth,0)
	   -- ++(0,-\waveheight)
	   -- ++(-#2*\wavewidth,0)
	   -- cycle
	    ;
	\draw ([yshift= 0.5*\waveheight]last brick) -- ++(#2*\wavewidth,0)
	      ([yshift=-0.5*\waveheight]last brick) -- ++(#2*\wavewidth,0)
	    ;
	
	\advancebrick{#2}
}

\newcommand{\brickx}[2]{        \brickgenericbus{#1}{#2}{wave x}}
\newcommand{\brickbus}[2]{      \brickgenericbus{#1}{#2}{wave bus}}
\newcommand{\brickbusyellow}[2]{\brickgenericbus{#1}{#2}{wave busyellow}}
\newcommand{\brickbusorange}[2]{\brickgenericbus{#1}{#2}{wave busorange}}
\newcommand{\brickbusblue}[2]{  \brickgenericbus{#1}{#2}{wave busblue}}


% Straight line signals
%  #1: 0 for odd, 1 for even half-ticks
%  #2: brick width
%  #3: Line offset (from center)
%  #4: Line style
\newcommand{\brickgenericline}[4]{
	\draw [#4] ([yshift=#3]last brick) -- ++(#2*\wavewidth,0);
	\advancebrick{#2}
}

\newcommand{\brickz}[2]{            \brickgenericline{#1}{#2}{0}{}}

\newcommand{\brickhigh}[2]{         \brickgenericline{#1}{#2}{ 0.5*\waveheight}{}}
\newcommand{\bricklow}[2]{          \brickgenericline{#1}{#2}{-0.5*\waveheight}{}}

\newcommand{\brickclkhigh}[2]{      \brickgenericline{#1}{#2}{ 0.5*\waveheight}{}}
\newcommand{\brickclklow}[2]{       \brickgenericline{#1}{#2}{-0.5*\waveheight}{}}

\newcommand{\brickclkhigharrow}[2]{ \brickgenericline{#1}{#2}{ 0.5*\waveheight}{}}
\newcommand{\brickclklowarrow}[2]{  \brickgenericline{#1}{#2}{-0.5*\waveheight}{}}

\newcommand{\brickpullup}[2]{       \brickgenericline{#1}{#2}{ 0.5*\waveheight}{wave pulled}}
\newcommand{\brickpulldown}[2]{     \brickgenericline{#1}{#2}{-0.5*\waveheight}{wave pulled}}


% Clock signals
%  #1: 0 for odd, 1 for even half-ticks
%  #2: brick width
%  #3: First-edge line offset (from center)
%  #4: 0 no arrow, 1 arrow
\newcommand{\brickgenericclk}[4]{
	\pgfmathsetlengthmacro{\voffset}{(1-(2*#1)) * #3*\waveheight}
	
	% Draw the clock
	\draw ([yshift=-0.5*\voffset]last brick)
	   -- ++(0,\voffset)
	   -- ++(#2*\wavewidth,0);
	
	% Add arrow
	\ifthenelse{\equal{#1}{0}}{
		\ifthenelse{\equal{#4}{1}}{
			\path [decoration={ markings
			                  , mark=at position 0.5 with {\arrow{>}}
			                  }
			      , postaction={decorate}
			      ]
			      ([yshift=-0.5*\voffset]last brick)
			   -- ++(0,\voffset);
		}{}
	}{}
	
	\advancebrick{#2}
}

\newcommand{\brickpclk}[2]{      \brickgenericclk{#1}{#2}{ 1.0}{0}}
\newcommand{\bricknclk}[2]{      \brickgenericclk{#1}{#2}{-1.0}{0}}
\newcommand{\brickpclkarrow}[2]{ \brickgenericclk{#1}{#2}{ 1.0}{1}}
\newcommand{\bricknclkarrow}[2]{ \brickgenericclk{#1}{#2}{-1.0}{1}}


% Sharp transitions
%  #1: brick width
%  #2: Edge start (offset from center)
%  #3: Edge end (offset from center)
%  #4: 0 no arrow, 1 arrow
\newcommand{\brickgenericsharptransition}[4]{
	\pgfmathsetlengthmacro{\vstart}{#2*\waveheight}
	\pgfmathsetlengthmacro{\vend}{#3*\waveheight}
	
	% Draw edge
	\draw ([yshift=0.5*\vstart]last brick)
	   -- ([yshift=0.5*\vend]last brick)
	   -- ++(#1*\wavewidth,0);
	
	% Add arrow
	\ifthenelse{\equal{#4}{1}}{
		\path [decoration={ markings
		                  , mark=at position 0.5 with {\arrow{>}}
		                  }
		      , postaction={decorate}
		      ]
		      ([yshift=0.5*\vstart]last brick)
		   -- ([yshift=0.5*\vend]last brick);
	}{}
	
	\advancebrick{#1}
}


% Soft transitions
%  #1: brick width
%  #2: Edge start (offset from center)
%  #3: Edge end (offset from center)
\newcommand{\brickgenericsofttransition}[3]{
	\pgfmathsetlengthmacro{\vstart}{#2*\waveheight}
	\pgfmathsetlengthmacro{\vend}{#3*\waveheight}
	
	\draw ([yshift=0.5*\vstart]last brick)
	   -- ([yshift=0.5*\vend, xshift=\transitionwidth]last brick)
	   -- ++(#1*\wavewidth - \transitionwidth,0);
	
	\advancebrick{#1}
}


% Short soft transitions
%  #1: brick width
%  #2: Edge start (offset from center)
%  #3: Edge end (offset from center)
\newcommand{\brickgenericshortsofttransition}[3]{
	\pgfmathsetlengthmacro{\vstart}{#2*\waveheight}
	\pgfmathsetlengthmacro{\vend}{#3*\waveheight}
	
	\draw ([yshift=0.5*\vstart]                             last brick)
	   -- ([yshift=0.5*\vstart, xshift=0.5*\transitionwidth]last brick)
	   -- ([yshift=0.5*\vend,   xshift=    \transitionwidth]last brick)
	   -- ++(#1*\wavewidth - \transitionwidth,0);
	
	\advancebrick{#1}
}


% Slow (curved) transitions
%  #1: brick width
%  #2: Edge start (offset from center)
%  #3: Edge end (offset from center)
%  #4: Line style
\newcommand{\brickgenericslowtransition}[4]{
	\pgfmathsetlengthmacro{\vstart}{#2*\waveheight}
	\pgfmathsetlengthmacro{\vend}{#3*\waveheight}
	
	\draw [#4]
	      ([yshift=0.5*\vstart]last brick)
	   .. controls ([yshift=0.5*\vstart]last brick)
	           and ([yshift=0.5*\vend, xshift=0.2*\slowtransitionwidth]last brick)
	   .. ([yshift=0.5*\vend, xshift=\slowtransitionwidth]last brick)
	   -- ++(#1*\wavewidth - \slowtransitionwidth,0);
	
	\advancebrick{#1}
}


% Transient transitions
%  #1: brick width
%  #2: Edge start (offset from center)
\newcommand{\brickgenerictransienttransition}[2]{
	\pgfmathsetlengthmacro{\voffset}{#2*\waveheight}
	
	\draw ([yshift=0.5*\voffset]last brick)
	   -- ([xshift=0.5*\transitionwidth]last brick)
	   -- ([yshift=0.5*\voffset, xshift=\transitionwidth]last brick)
	   -- ++(#1*\wavewidth - \transitionwidth,0);
	
	\advancebrick{#1}
}


% Soft transitions between buses
%  #1: brick width
%  #2: Start bus style
%  #3: End bus style
\newcommand{\brickgenericbustransition}[3]{
	% Close-off starting bus
	\draw [#2]
	      ([yshift= 0.5*\waveheight]last brick)
	   -- ([xshift= 0.5*\transitionwidth]last brick)
	   -- ([yshift=-0.5*\waveheight]last brick);
	
	% Open-up ending bus
	\draw [#3]
	      ([xshift= \wavewidth,           yshift= 0.5*\waveheight]last brick)
	   -- ([xshift= 1.0*\transitionwidth, yshift= 0.5*\waveheight]last brick)
	   -- ([xshift= 0.5*\transitionwidth]last brick)
	   -- ([xshift= 1.0*\transitionwidth, yshift=-0.5*\waveheight]last brick)
	   -- ([xshift= \wavewidth,           yshift=-0.5*\waveheight]last brick)
	   ;
	
	\advancebrick{#1}
}


% Soft transitions into buses
%  #1: brick width
%  #2: Start edge (offset from center)
%  #3: End bus style
\newcommand{\brickgenericbusintransition}[3]{
	\pgfmathsetlengthmacro{\voffset}{#2*\waveheight}
	
	% Open-up ending bus
	\draw [#3]
	      ([xshift= \wavewidth,           yshift= 0.5*\waveheight]last brick)
	   -- ([xshift= 1.0*\transitionwidth, yshift= 0.5*\waveheight]last brick)
	   -- ([                              yshift= 0.5*\voffset]   last brick)
	   -- ([xshift= 1.0*\transitionwidth, yshift=-0.5*\waveheight]last brick)
	   -- ([xshift= \wavewidth,           yshift=-0.5*\waveheight]last brick)
	   ;
	
	\advancebrick{#1}
}

% Clk constants transitions
\newcommand{\bricktoclkhigh}[1]{ \brickgenericsharptransition{#1}{-1}{ 1}{0}}
\newcommand{\bricktoclklow}[1]{  \brickgenericsharptransition{#1}{ 1}{-1}{0}}

\newcommand{\bricktoclkhigharrow}[1]{ \brickgenericsharptransition{#1}{-1}{ 1}{1}}
\newcommand{\bricktoclklowarrow}[1]{  \brickgenericsharptransition{#1}{ 1}{-1}{1}}

% Soft transitions to 1 and 0
\newcommand{        \bricklowtohigh}[1]{ \brickgenericsofttransition{#1}{-1}{ 1}}
\newcommand{       \brickpclktohigh}[1]{ \brickgenericsofttransition{#1}{-1}{ 1}}
\newcommand{  \brickpclkarrowtohigh}[1]{ \brickgenericsofttransition{#1}{-1}{ 1}}
\newcommand{     \brickclklowtohigh}[1]{ \brickgenericsofttransition{#1}{-1}{ 1}}
\newcommand{\brickclklowarrowtohigh}[1]{ \brickgenericsofttransition{#1}{-1}{ 1}}
\newcommand{   \brickpulldowntohigh}[1]{ \brickgenericsofttransition{#1}{-1}{ 1}}

\newcommand{        \brickhightolow}[1]{ \brickgenericsofttransition{#1}{ 1}{-1}}
\newcommand{        \bricknclktolow}[1]{ \brickgenericsofttransition{#1}{ 1}{-1}}
\newcommand{   \bricknclkarrowtolow}[1]{ \brickgenericsofttransition{#1}{ 1}{-1}}
\newcommand{     \brickclkhightolow}[1]{ \brickgenericsofttransition{#1}{ 1}{-1}}
\newcommand{\brickclkhigharrowtolow}[1]{ \brickgenericsofttransition{#1}{ 1}{-1}}
\newcommand{      \brickpulluptolow}[1]{ \brickgenericsofttransition{#1}{ 1}{-1}}

% Soft short transitions to 1 and 0
\newcommand{\brickztohigh}[1]{ \brickgenericshortsofttransition{#1}{0}{ 1}}
\newcommand{\brickztolow}[1]{  \brickgenericshortsofttransition{#1}{0}{-1}}

% Transient transitions to 1 and 0
\newcommand{        \brickhightohigh}[1]{\brickgenerictransienttransition{#1}{ 1}}
\newcommand{        \bricknclktohigh}[1]{\brickgenerictransienttransition{#1}{ 1}}
\newcommand{   \bricknclkarrowtohigh}[1]{\brickgenerictransienttransition{#1}{ 1}}
\newcommand{     \brickclkhightohigh}[1]{\brickgenerictransienttransition{#1}{ 1}}
\newcommand{\brickclkhigharrowtohigh}[1]{\brickgenerictransienttransition{#1}{ 1}}

\newcommand{        \bricklowtolow}[1]{\brickgenerictransienttransition{#1}{-1}}
\newcommand{       \brickpclktolow}[1]{\brickgenerictransienttransition{#1}{-1}}
\newcommand{  \brickpclkarrowtolow}[1]{\brickgenerictransienttransition{#1}{-1}}
\newcommand{     \brickclklowtolow}[1]{\brickgenerictransienttransition{#1}{-1}}
\newcommand{\brickclklowarrowtolow}[1]{\brickgenerictransienttransition{#1}{-1}}

% Slow, curved transitions
\newcommand{        \brickhightoz}[1]{\brickgenericslowtransition{#1}{ 1}{ 0}{}}
\newcommand{        \bricknclktoz}[1]{\brickgenericslowtransition{#1}{ 1}{ 0}{}}
\newcommand{   \bricknclkarrowtoz}[1]{\brickgenericslowtransition{#1}{ 1}{ 0}{}}
\newcommand{     \brickclkhightoz}[1]{\brickgenericslowtransition{#1}{ 1}{ 0}{}}
\newcommand{\brickclkhigharrowtoz}[1]{\brickgenericslowtransition{#1}{ 1}{ 0}{}}
\newcommand{      \brickpulluptoz}[1]{\brickgenericslowtransition{#1}{ 1}{ 0}{}}

\newcommand{        \bricklowtoz}[1]{\brickgenericslowtransition{#1}{-1}{ 0}{}}
\newcommand{       \brickpclktoz}[1]{\brickgenericslowtransition{#1}{-1}{ 0}{}}
\newcommand{  \brickpclkarrowtoz}[1]{\brickgenericslowtransition{#1}{-1}{ 0}{}}
\newcommand{     \brickclklowtoz}[1]{\brickgenericslowtransition{#1}{-1}{ 0}{}}
\newcommand{\brickclklowarrowtoz}[1]{\brickgenericslowtransition{#1}{-1}{ 0}{}}
\newcommand{   \brickpulldowntoz}[1]{\brickgenericslowtransition{#1}{-1}{ 0}{}}

\newcommand{        \bricklowtopullup}[1]{\brickgenericslowtransition{#1}{-1}{ 1}{wave pulled}}
\newcommand{       \brickpclktopullup}[1]{\brickgenericslowtransition{#1}{-1}{ 1}{wave pulled}}
\newcommand{  \brickpclkarrowtopullup}[1]{\brickgenericslowtransition{#1}{-1}{ 1}{wave pulled}}
\newcommand{     \brickclklowtopullup}[1]{\brickgenericslowtransition{#1}{-1}{ 1}{wave pulled}}
\newcommand{\brickclklowarrowtopullup}[1]{\brickgenericslowtransition{#1}{-1}{ 1}{wave pulled}}
\newcommand{   \brickpulldowntopullup}[1]{\brickgenericslowtransition{#1}{-1}{ 1}{wave pulled}}

\newcommand{        \brickhightopulldown}[1]{\brickgenericslowtransition{#1}{ 1}{-1}{wave pulled}}
\newcommand{        \bricknclktopulldown}[1]{\brickgenericslowtransition{#1}{ 1}{-1}{wave pulled}}
\newcommand{   \bricknclkarrowtopulldown}[1]{\brickgenericslowtransition{#1}{ 1}{-1}{wave pulled}}
\newcommand{     \brickclkhightopulldown}[1]{\brickgenericslowtransition{#1}{ 1}{-1}{wave pulled}}
\newcommand{\brickclkhigharrowtopulldown}[1]{\brickgenericslowtransition{#1}{ 1}{-1}{wave pulled}}
\newcommand{      \brickpulluptopulldown}[1]{\brickgenericslowtransition{#1}{ 1}{-1}{wave pulled}}

\newcommand{  \brickztopullup}[1]{\brickgenericslowtransition{#1}{ 0}{ 1}{wave pulled}}
\newcommand{\brickztopulldown}[1]{\brickgenericslowtransition{#1}{ 0}{-1}{wave pulled}}

% Bus transitions
\newcommand{      \brickbustox}[1]{\brickgenericbustransition{#1}{wave bus}{      wave x}}
\newcommand{\brickbusyellowtox}[1]{\brickgenericbustransition{#1}{wave busyellow}{wave x}}
\newcommand{\brickbusorangetox}[1]{\brickgenericbustransition{#1}{wave busorange}{wave x}}
\newcommand{  \brickbusbluetox}[1]{\brickgenericbustransition{#1}{wave busblue}{  wave x}}

\newcommand{        \brickxtobus}[1]{\brickgenericbustransition{#1}{wave x}{        wave bus}}
\newcommand{      \brickbustobus}[1]{\brickgenericbustransition{#1}{wave bus}{      wave bus}}
\newcommand{\brickbusyellowtobus}[1]{\brickgenericbustransition{#1}{wave busyellow}{wave bus}}
\newcommand{\brickbusorangetobus}[1]{\brickgenericbustransition{#1}{wave busorange}{wave bus}}
\newcommand{  \brickbusbluetobus}[1]{\brickgenericbustransition{#1}{wave busblue}{  wave bus}}

\newcommand{        \brickxtobusyellow}[1]{\brickgenericbustransition{#1}{wave x}{        wave busyellow}}
\newcommand{      \brickbustobusyellow}[1]{\brickgenericbustransition{#1}{wave bus}{      wave busyellow}}
\newcommand{\brickbusyellowtobusyellow}[1]{\brickgenericbustransition{#1}{wave busyellow}{wave busyellow}}
\newcommand{\brickbusorangetobusyellow}[1]{\brickgenericbustransition{#1}{wave busorange}{wave busyellow}}
\newcommand{  \brickbusbluetobusyellow}[1]{\brickgenericbustransition{#1}{wave busblue}{  wave busyellow}}

\newcommand{        \brickxtobusorange}[1]{\brickgenericbustransition{#1}{wave x}{        wave busorange}}
\newcommand{      \brickbustobusorange}[1]{\brickgenericbustransition{#1}{wave bus}{      wave busorange}}
\newcommand{\brickbusyellowtobusorange}[1]{\brickgenericbustransition{#1}{wave busyellow}{wave busorange}}
\newcommand{\brickbusorangetobusorange}[1]{\brickgenericbustransition{#1}{wave busorange}{wave busorange}}
\newcommand{  \brickbusbluetobusorange}[1]{\brickgenericbustransition{#1}{wave busblue}{  wave busorange}}

\newcommand{        \brickxtobusblue}[1]{\brickgenericbustransition{#1}{wave x}{        wave busblue}}
\newcommand{      \brickbustobusblue}[1]{\brickgenericbustransition{#1}{wave bus}{      wave busblue}}
\newcommand{\brickbusyellowtobusblue}[1]{\brickgenericbustransition{#1}{wave busyellow}{wave busblue}}
\newcommand{\brickbusorangetobusblue}[1]{\brickgenericbustransition{#1}{wave busorange}{wave busblue}}
\newcommand{  \brickbusbluetobusblue}[1]{\brickgenericbustransition{#1}{wave busblue}{  wave busblue}}

% Soft transitions into busses
\newcommand{        \bricklowtox}[1]{\brickgenericbusintransition{#1}{-1.0}{wave x}}
\newcommand{      \bricklowtobus}[1]{\brickgenericbusintransition{#1}{-1.0}{wave bus}}
\newcommand{\bricklowtobusyellow}[1]{\brickgenericbusintransition{#1}{-1.0}{wave busyellow}}
\newcommand{\bricklowtobusorange}[1]{\brickgenericbusintransition{#1}{-1.0}{wave busorange}}
\newcommand{  \bricklowtobusblue}[1]{\brickgenericbusintransition{#1}{-1.0}{wave busblue}}

\newcommand{        \brickpclktox}[1]{\brickgenericbusintransition{#1}{-1.0}{wave x}}
\newcommand{      \brickpclktobus}[1]{\brickgenericbusintransition{#1}{-1.0}{wave bus}}
\newcommand{\brickpclktobusyellow}[1]{\brickgenericbusintransition{#1}{-1.0}{wave busyellow}}
\newcommand{\brickpclktobusorange}[1]{\brickgenericbusintransition{#1}{-1.0}{wave busorange}}
\newcommand{  \brickpclktobusblue}[1]{\brickgenericbusintransition{#1}{-1.0}{wave busblue}}

\newcommand{        \brickpclkarrowtox}[1]{\brickgenericbusintransition{#1}{-1.0}{wave x}}
\newcommand{      \brickpclkarrowtobus}[1]{\brickgenericbusintransition{#1}{-1.0}{wave bus}}
\newcommand{\brickpclkarrowtobusyellow}[1]{\brickgenericbusintransition{#1}{-1.0}{wave busyellow}}
\newcommand{\brickpclkarrowtobusorange}[1]{\brickgenericbusintransition{#1}{-1.0}{wave busorange}}
\newcommand{  \brickpclkarrowtobusblue}[1]{\brickgenericbusintransition{#1}{-1.0}{wave busblue}}

\newcommand{        \brickclklowtox}[1]{\brickgenericbusintransition{#1}{-1.0}{wave x}}
\newcommand{      \brickclklowtobus}[1]{\brickgenericbusintransition{#1}{-1.0}{wave bus}}
\newcommand{\brickclklowtobusyellow}[1]{\brickgenericbusintransition{#1}{-1.0}{wave busyellow}}
\newcommand{\brickclklowtobusorange}[1]{\brickgenericbusintransition{#1}{-1.0}{wave busorange}}
\newcommand{  \brickclklowtobusblue}[1]{\brickgenericbusintransition{#1}{-1.0}{wave busblue}}

\newcommand{        \brickclklowarrowtox}[1]{\brickgenericbusintransition{#1}{-1.0}{wave x}}
\newcommand{      \brickclklowarrowtobus}[1]{\brickgenericbusintransition{#1}{-1.0}{wave bus}}
\newcommand{\brickclklowarrowtobusyellow}[1]{\brickgenericbusintransition{#1}{-1.0}{wave busyellow}}
\newcommand{\brickclklowarrowtobusorange}[1]{\brickgenericbusintransition{#1}{-1.0}{wave busorange}}
\newcommand{  \brickclklowarrowtobusblue}[1]{\brickgenericbusintransition{#1}{-1.0}{wave busblue}}

\newcommand{        \brickhightox}[1]{\brickgenericbusintransition{#1}{ 1.0}{wave x}}
\newcommand{      \brickhightobus}[1]{\brickgenericbusintransition{#1}{ 1.0}{wave bus}}
\newcommand{\brickhightobusyellow}[1]{\brickgenericbusintransition{#1}{ 1.0}{wave busyellow}}
\newcommand{\brickhightobusorange}[1]{\brickgenericbusintransition{#1}{ 1.0}{wave busorange}}
\newcommand{  \brickhightobusblue}[1]{\brickgenericbusintransition{#1}{ 1.0}{wave busblue}}

\newcommand{        \bricknclktox}[1]{\brickgenericbusintransition{#1}{ 1.0}{wave x}}
\newcommand{      \bricknclktobus}[1]{\brickgenericbusintransition{#1}{ 1.0}{wave bus}}
\newcommand{\bricknclktobusyellow}[1]{\brickgenericbusintransition{#1}{ 1.0}{wave busyellow}}
\newcommand{\bricknclktobusorange}[1]{\brickgenericbusintransition{#1}{ 1.0}{wave busorange}}
\newcommand{  \bricknclktobusblue}[1]{\brickgenericbusintransition{#1}{ 1.0}{wave busblue}}

\newcommand{        \bricknclkarrowtox}[1]{\brickgenericbusintransition{#1}{ 1.0}{wave x}}
\newcommand{      \bricknclkarrowtobus}[1]{\brickgenericbusintransition{#1}{ 1.0}{wave bus}}
\newcommand{\bricknclkarrowtobusyellow}[1]{\brickgenericbusintransition{#1}{ 1.0}{wave busyellow}}
\newcommand{\bricknclkarrowtobusorange}[1]{\brickgenericbusintransition{#1}{ 1.0}{wave busorange}}
\newcommand{  \bricknclkarrowtobusblue}[1]{\brickgenericbusintransition{#1}{ 1.0}{wave busblue}}

\newcommand{        \brickclkhightox}[1]{\brickgenericbusintransition{#1}{ 1.0}{wave x}}
\newcommand{      \brickclkhightobus}[1]{\brickgenericbusintransition{#1}{ 1.0}{wave bus}}
\newcommand{\brickclkhightobusyellow}[1]{\brickgenericbusintransition{#1}{ 1.0}{wave busyellow}}
\newcommand{\brickclkhightobusorange}[1]{\brickgenericbusintransition{#1}{ 1.0}{wave busorange}}
\newcommand{  \brickclkhightobusblue}[1]{\brickgenericbusintransition{#1}{ 1.0}{wave busblue}}

\newcommand{        \brickclkhigharrowtox}[1]{\brickgenericbusintransition{#1}{ 1.0}{wave x}}
\newcommand{      \brickclkhigharrowtobus}[1]{\brickgenericbusintransition{#1}{ 1.0}{wave bus}}
\newcommand{\brickclkhigharrowtobusyellow}[1]{\brickgenericbusintransition{#1}{ 1.0}{wave busyellow}}
\newcommand{\brickclkhigharrowtobusorange}[1]{\brickgenericbusintransition{#1}{ 1.0}{wave busorange}}
\newcommand{  \brickclkhigharrowtobusblue}[1]{\brickgenericbusintransition{#1}{ 1.0}{wave busblue}}



"""

# Mapping from wave values to tikz brick names
TIKZ_SIG_NAMES = {
	"x": "x",
	"z": "z",
	"0": "low",
	"1": "high",
	"2": "bus",
	"=": "bus",
	"3": "busyellow",
	"4": "busorange",
	"5": "busblue",
	"p": "pclk",
	"P": "pclkarrow",
	"n": "nclk",
	"N": "nclkarrow",
	"l": "clklow",
	"L": "clklowarrow",
	"h": "clkhigh",
	"H": "clkhigharrow",
	"u": "pullup",
	"d": "pulldown",
}


# A list of tikz signal name pairs for which custom transitions exist
HAS_TRANSITION = set(re.findall( r"\\brick([a-z]+)?to([a-z]+)"
                               , TIKZ_HEADER
                               , re.I
                               )
                    )


def render_waveform(signal_params):
	"""
	Produce TikZ for just the waveform of a given signal.
	"""
	wave   = signal_params["wave"]
	phase  = signal_params.get("phase", 0.0)
	period = signal_params.get("period", 1.0)
	
	assert phase  >= 0.0, "Phase must be positive or zero."
	assert period >= 0.0, "Period must be positive or zero."
	
	out = [r"\coordinate (last brick) at (wave start);"]
	out.append(r"\begin{scope}[line cap=rect, line join=round];")
	
	# Start assuming the signal is x if not otherwise specified
	last_signal = "x" if wave[0] == "." else wave[0]
	
	def get_brick(signal, odd_even):
		return(r"\brick%s{%d}{%f}"%(
		        TIKZ_SIG_NAMES[signal],
		        odd_even,
		        period,
		      ))
	
	def get_transition_brick(last_signal, signal):
		if ("", TIKZ_SIG_NAMES[signal]) in HAS_TRANSITION:
			# Use A custom universal transition brick
			return(r"\brickto%s{%f}"%(
			        TIKZ_SIG_NAMES[signal],
			        period,
			      ))
		if (TIKZ_SIG_NAMES[last_signal], TIKZ_SIG_NAMES[signal]) in HAS_TRANSITION:
			# Use A custom transition brick
			return(r"\brick%sto%s{%f}"%(
			        TIKZ_SIG_NAMES[last_signal],
			        TIKZ_SIG_NAMES[signal],
			        period,
			      ))
		else:
			# No specific transition, just abutt the two bricks
			return(r"\brick%s{0}{%f}"%(
			        TIKZ_SIG_NAMES[signal],
			        period,
			      ))
	
	# Draw the first part of the waveform to get the phase right
	if phase != 0.0:
		if (phase*2)%1.0 != 0.0:
			out.append(r"\truncatebrick{%f}{%f}{%s}"%(
			            period,
			            1.0-(phase*2)%1.0,
			            get_brick(last_signal, int(phase*2.0+1)%2)
			          ))
		for i in range(int(phase*2)):
			out.append(get_brick(last_signal, (int(phase*2.0) - i)%2))
	
	# Draw the waveform, one timeslot at a time
	for time, signal in enumerate(wave):
		continued_signal = last_signal if signal == "." else signal
		if time == 0 or signal == ".":
			out.append(get_brick(continued_signal, 0))
		else:
			out.append(get_transition_brick(last_signal, continued_signal))
		
		out.append(get_brick(continued_signal, 1))
		
		last_signal = continued_signal
	
	out.append(r"\end{scope};")
	return "\n".join(out)


def render_signal(signal_params, tikz_position="(0,0)"):
	"""
	Produce a TikZ string defining the given waveform line with parameters as used
	by WaveDrom.
	"""
	return r"""
		\coordinate (wave start) at %s;
		\signallabel{%s}
		%s
	"""%(
		tikz_position,
		signal_params.get("name", ""),
		render_waveform(signal_params)
	)


def render_wavedrom(wavedrom):
	return r"""
		\begin{tikzpicture}
			%s
			%s
		\end{tikzpicture}
	"""%(TIKZ_HEADER, render_signal(wavedrom))


if __name__=="__main__":
	print(render_wavedrom( { "name": "test"
	                       , "wave": "0x0=030405"
	                       , "phase": 0.0
	                       , "period": 1.0
	                       }
	                     )
	     )
