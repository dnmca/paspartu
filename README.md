# Paspartu - preserve the stories behind your old photos

### Motivation

Few month ago I started to digitize by old family photo albums.
Those old photos have been glued to the album pages and when I pilled them off, 
I noticed that a lot of pictures had a handwritten massage on the back. 

<img src="./images/original.png" alt="drawing" width="400"/>

Of course, I've seen those before, but this time I understood for the first time how 
immensely valuable they are.

If you think about it, what is the most important component of the photo? Its quality? Rarity? Form? Significance of 
the person or event captured? Story behind the photo? 

Possibly each of those is important in its own way. But it seems to be that the most powerful virtue is the 
story behind the photograph. Who made a shot? When? Where? Who are those people on the photo? What were the 
circumstances of its creation? Where are those people now? Those are the things we ask when we look through 
old photo albums. And old photos without context have little value, especially if we are talking 
about family pictures, which rarely depict anything of historical significance.

Besides messages on the back of the photographs, the most important "photo metadata" is stored in the form of 
memories of your elder relatives. But memory is fragile thing, as well as human life. 
It is lost if it is not preserved in time.

I came to me that it's really important to preserve old photos' stories for my ancestors 
(or other relatives interested in our family history). And I wanted to do it as soon as possible, while
people who can tell these stories are still alive.
 
 This led to the creation of this tool. I wanted it to be simple, fast and offline. So in case its functionality
 seems limited to you, it is so by design. 

### Tool

This tool allows you to add arbitrary-size caption to your photos without losing 
image quality.

<img src="./images/captioned.jpg" alt="drawing" width="400"/>

Functionality:

- Zoom in/out (`Ctrl +`/`Ctrl -`)
- Supported formats: PNG and JPEG
- Original image quality is preserved
- Original image is backuped
- Font size is controlled by `TEXT_WIDTH` constant, which defines # of characters per line
- Font face is controlled by the `FONT_PATH` constant. You can use your custom font if you would like.

### Workflow

0) Prerequisites:
    ```
    python >= 3.7
    pip >= 19.2.3
    ```
1) Install required packages
    ```shell script
    pip install -r requirements.txt
    ```
2) Launch tool:
    ```shell script
    python paspartu.py
    ```
3) Open image (`Open` button)
4) Enter text in text box
5) Save captioned image (`Save` button)
> 2 folders are created in image parent directory: `target` and `backup`. 
> Former for captioned images and later for original ones.

### Contribution

Feel free to contribute to this project if you like it.
Any suggestions, comments or bug reports are appreciated.

