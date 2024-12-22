# 何以為此案
此案乃為期末之時，師欲使吾等，以套接字，創一案；
而後，案結，而非師之訴願矣，且欲使吾等，創新一案；
而其新案之限，乃餘五日，吾徹夜不懈怠，為組內所耗心費神，而創此案；

# 何以行此案
欲行此案，必對此案所賴之基底，安之，裝之；
此案亦賴於五，python3.8，一也，cv2，二也，PIL，三也，pyaudio，四也，tkinter，五也；
而若欲行此案於一心淨土，得以anaconda安而裝之；
而創anaconda之境之刻，亦可以python3.8為其數，得使python3.8安而裝之；

    conda create -n open_meeting python=3.8
    conda activate open_meeting
    pip install requirements

待其賴者立於爾等之地，得以一終端，運以python，喚其名曰server.py；

    python server.py

而後，再以另一終端，視client.py，改其數host為行以server.py之終端之ip；
再改其數local_host，為本機之ip，並運以python，喚其名曰client.py；

    python client.py

此案運之；
而若有他者，連以同一ip，爾等亦可通之；