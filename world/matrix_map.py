# Long test map to test camera scroll: TERRAIN
TERRAIN_MAP = [
    "                                                  ",  
    "                                                  ", 
    "                                                  ", 
    "  2233                    2233                    ", 
    "          (- - 8 8 8 8 8 8        (- - 8 8 8 8 8 8", 
    "      [== 78 8 0 0 0 0 0 0    [== 78 8 0 0 0 0 0 0", 
    "-5===5------68 0 0 0 0 0 0-5= =5- - - 68 0 0 0 0 0", 
    "0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 ", 
]

# DECO MAP (Mask Map)
DECO_MAP = [
    "                                                  ", 
    "    ff                                            ", 
    "                                                  ", 
    "                          S                       ", # f: hàng rào, S: Shop
    "          g g              l      g g             ", # g: cỏ, l: đèn
    "      r   r                       r               ", # r: đá
    "                                                  ", 
    "                                                  ", 
]

# INTERACT MAP (Layer dành riêng cho vật thể tương tác)
# 'B' = Box (Thùng đẩy)
# 'b' = Barrel (Thùng phuy đập vỡ)
# 'C' = Chest (Rương)
INTERACT_MAP = [
    "                                                  ", 
    "                                                  ", 
    "   C                                               ", 
    "                                                  ", # Thùng đẩy trên cao
    "        b                         b               ", # Rương và Thùng phuy
    " B                                                ", 
    "                                                  ", 
    "                                                  ", 
]