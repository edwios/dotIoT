#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef unsigned char u8;
typedef unsigned short u16;

typedef enum {
    AT_RESULT_CODE_OK = 0,
    AT_RESULT_CODE_ERROR,
    AT_RESULT_CODE_INVALID,
    AT_RESULT_CODE_MAX,
} at_result_code_string_index_t;

u8 HEX2BYTE(u8 hex_ch)
{
	if (hex_ch >= '0' && hex_ch <= '9')
	{
		return hex_ch - '0';
	}

	if (hex_ch >= 'a' && hex_ch <= 'f')
	{
		return hex_ch - 'a' + 10;
	}

	if (hex_ch >= 'A' && hex_ch <= 'F')
	{
		return hex_ch - 'A' + 10;
	}

	return 0x00;
}

u8 HEX2BIN(u8 * p_hexstr, u8 * p_binstr)
{
	u8 bin_len = 0;
	u8 hex_len = strlen((char *)p_hexstr);
	u8 index = 0;

	if (hex_len % 2 == 1)
	{
		hex_len -= 1;
	}

	bin_len = hex_len / 2;
	for(index = 0; index < hex_len; index+=2)
	{
		p_binstr[index/2] = ((HEX2BYTE(p_hexstr[index]) << 4) & 0xF0) + HEX2BYTE(p_hexstr[index + 1]); 
	}

	return bin_len;
}

u16 HEX2U16(u8 * p_hexstr) //将16进制字符串转换成U16类型的整数
{
	u8 hexStr_len = strlen((char *)p_hexstr);
	u16 numBer = 0;
	u8 index = 0;

	for(index = 0; index < hexStr_len; index++)
	{
		numBer <<=4;
		numBer += HEX2BYTE(p_hexstr[index]);
	}

	return numBer;
}

u16 STR2U16(u8 * p_hexstr) //将10进制字符串转换成U16类型的整数
{
	u8 hexStr_len = strlen((char *)p_hexstr);
	u16 numBer = 0;
	u8 index = 0;

	for(index = 0; index < hexStr_len; index++)
	{
		numBer *= 10;
		numBer += HEX2BYTE(p_hexstr[index]);
	}

	return numBer;
}

void at_mesh_tx_cmd(u16 dst, u8 *data, u8 len, u8 app)
{
    printf("Dst: %04x\n", dst);
    printf("Len: %d\n", len);
    printf("Op code: %02x\n", data[0]);
    printf("Pars: ");
    for(int i=1; i<len; i++)
    {
        printf("%02x", data[i]);
    }
    printf("\n");
}

static unsigned char atCmd_Send(char *pbuf,  int mode, int lenth)
{
	char * tmp = strstr(pbuf,",");
    if(tmp == NULL)
    {
        return AT_RESULT_CODE_ERROR;
    }

	tmp[0] = 0; tmp++;

	u16 addr_dst = HEX2U16(pbuf);  //获取目的地址

	pbuf = tmp;

	tmp = strstr(pbuf,",");
    if(tmp == NULL)
    {
        return AT_RESULT_CODE_ERROR;
    }
	tmp[0] = 0; tmp++;

	u16 data_len = STR2U16(pbuf); //获取数据长度

	pbuf[0] = 0; //handle 0：module 2 module，handle 1：modul 2 app

	#if 1
	u8 btmp[17];
	u8 stmp[33];
	u8 bl = 0;

	while(data_len > 0)
	{
		if(data_len > 16)
		{
			stmp[0] = 0;
			strncpy(stmp, tmp, 32);
			stmp[32] = 0;
			bl = HEX2BIN(stmp, btmp);
			at_mesh_tx_cmd(addr_dst, btmp, bl, pbuf[0]);
			data_len -= bl;
			tmp +=32;	// 16 bytes = 32 hex digits
		}
		else
		{
			stmp[0] = 0;
			strncpy(stmp, tmp, 32);
			stmp[32] = 0;
			bl = HEX2BIN(stmp, btmp);
			at_mesh_tx_cmd(addr_dst, btmp, bl, pbuf[0]);
			data_len = 0;
		}
	}
	#else
	static int cmd_sno = 0;
	cmd_sno = clock_time() + device_address;

	tmp -= 3;
	tmp[0] = 0x3f|0xc0;
	tmp[1] = data_len;
	mesh_push_user_command(cmd_sno++, addr_dst, tmp, 13);
	#endif

	if(addr_dst == 0xffff) return 0;
	return 0xff;
}

int main()
{
    u8 buffer[64] = "7,3,d0000000";
    atCmd_Send(buffer, 0, 0);
}
