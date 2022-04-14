
ffmpeg -i "simplescreenrecorder-2022-04-14_19.42.08.mkv" -to 0:00:22 -plays 0 -vf "fps=3,scale=800:-1" -pix_fmt pal8 tree.gif
