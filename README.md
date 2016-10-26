WaveDrom TikZ
=============

This simple (unofficial) tool is a translator from the language used by the
excellent [WaveDrom](http://wavedrom.github.io/) waveform drawing tool to TikZ
allowing for professional looking waveforms in LaTeX documents. By producing
TikZ, diagrams are typeset in native LaTeX and lines and shapes are drawn
consistently with other TikZ figures in a document. Further, more sophisticated
annotations are possible by referencing parts of the wavefrom from custom TikZ
code.

This tool is currently in an incomplete and largely undocumented state. All
drawing of waveforms should be supported correctly but arrows and annotations
are not.

## Example

A simple example waveform.

```
{
  signal: [
    { name : "clk",  wave : "p....|.." },
    { name : "data", wave : "x===.|.x", data: "a b c" },
    { name : "vld",  wave : "01...|.0" },
    { name : "rdy",  wave : "1..0.|1." },
  ]
}
```

Which can be built from within LaTeX source:

```
\begin{tikzpicture}[thick]
	\input{|"wavedromtikz.py wavedrom figures/rdyvld-protocol.drom"}
\end{tikzpicture}
```

Producing:

![WaveDromTikZ example waveform](http://jhnet.co.uk/misc/waveDromTikZ.png)

For comparison, the original WaveDrom image:

![Regular WaveDrom example waveform](http://jhnet.co.uk/misc/waveDrom.png)


### More Examples

Make the example pdf file from project root using

    ./make.sh
