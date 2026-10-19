/*
 * TokenKey RT - boot header for FlexSPI NOR XIP (IMXRT1060RM Rev.3, 9.6.3 / 9.7.1)
 *
 *   0x6000_0000  FlexSPI NOR configuration block (FCB), 512 B
 *   0x6000_1000  Image Vector Table (IVT), 32 B
 *   0x6000_1020  Boot data, 16 B
 *
 * Flash: Winbond W25Q64JV (8 MB) on FlexSPI A, primary pins GPIO_SD_B1_06..11.
 * DQS pad (GPIO_SD_B1_05) is not connected -> readSampleClkSrc = 0 (internal loopback),
 * which limits the serial clock; we run SDR quad I/O at 50 MHz (W25Q64JV: 133 MHz max).
 *
 * Requirement: the flash QE bit (SR2[1]) must be 1. W25Q64JV-IQ ships with QE=1; a part
 * with QE=0 will not boot in 1-4-4 mode (see README "Flash notes").
 */
#include <stdint.h>

/* ---- FlexSPI LUT encoding (RM 27.7.8): {opcode[15:10] pads[9:8] operand[7:0]} x2 ------ */
#define LUT_CMD_SDR     0x01u
#define LUT_RADDR_SDR   0x02u
#define LUT_WRITE_SDR   0x08u
#define LUT_READ_SDR    0x09u
#define LUT_DUMMY_SDR   0x0Cu
#define LUT_STOP        0x00u
#define PAD1            0x0u
#define PAD4            0x2u
#define LUT_SEQ(op0, pad0, arg0, op1, pad1, arg1)                                           \
    ((uint32_t)(((uint32_t)(arg0) & 0xFFu) | (((uint32_t)(pad0) & 0x3u) << 8) |             \
                (((uint32_t)(op0) & 0x3Fu) << 10) | (((uint32_t)(arg1) & 0xFFu) << 16) |    \
                (((uint32_t)(pad1) & 0x3u) << 24) | (((uint32_t)(op1) & 0x3Fu) << 26)))

typedef struct {
    uint32_t tag;                    /* 0x000 'FCFB' */
    uint32_t version;                /* 0x004 */
    uint32_t reserved0;              /* 0x008 */
    uint8_t readSampleClkSrc;        /* 0x00C 0 internal loopback, 1 DQS loopback, 3 flash DQS */
    uint8_t csHoldTime;              /* 0x00D */
    uint8_t csSetupTime;             /* 0x00E */
    uint8_t columnAddressWidth;      /* 0x00F */
    uint8_t deviceModeCfgEnable;     /* 0x010 */
    uint8_t deviceModeType;          /* 0x011 */
    uint16_t waitTimeCfgCommands;    /* 0x012 */
    uint32_t deviceModeSeq;          /* 0x014 */
    uint32_t deviceModeArg;          /* 0x018 */
    uint8_t configCmdEnable;         /* 0x01C */
    uint8_t configModeType[3];       /* 0x01D */
    uint32_t configCmdSeqs[3];       /* 0x020 */
    uint32_t reserved1;              /* 0x02C */
    uint32_t configCmdArgs[3];       /* 0x030 */
    uint32_t reserved2;              /* 0x03C */
    uint32_t controllerMiscOption;   /* 0x040 */
    uint8_t deviceType;              /* 0x044 1 = serial NOR */
    uint8_t sflashPadType;           /* 0x045 4 = quad */
    uint8_t serialClkFreq;           /* 0x046 1=30,2=50,3=60,4=75,5=80,6=100,7=120,8=133,9=166 MHz */
    uint8_t lutCustomSeqEnable;      /* 0x047 */
    uint32_t reserved3[2];           /* 0x048 */
    uint32_t sflashA1Size;           /* 0x050 */
    uint32_t sflashA2Size;           /* 0x054 */
    uint32_t sflashB1Size;           /* 0x058 */
    uint32_t sflashB2Size;           /* 0x05C */
    uint32_t csPadSettingOverride;   /* 0x060 */
    uint32_t sclkPadSettingOverride; /* 0x064 */
    uint32_t dataPadSettingOverride; /* 0x068 */
    uint32_t dqsPadSettingOverride;  /* 0x06C */
    uint32_t timeoutInMs;            /* 0x070 */
    uint32_t commandInterval;        /* 0x074 */
    uint16_t dataValidTime[2];       /* 0x078 */
    uint16_t busyOffset;             /* 0x07C */
    uint16_t busyBitPolarity;        /* 0x07E */
    uint32_t lookupTable[64];        /* 0x080 */
    uint32_t lutCustomSeq[12];       /* 0x180 */
    uint32_t reserved4[4];           /* 0x1B0 */
} flexspi_mem_config_t;              /* 448 B */

typedef struct {
    flexspi_mem_config_t memConfig;  /* 0x000 */
    uint32_t pageSize;               /* 0x1C0 */
    uint32_t sectorSize;             /* 0x1C4 */
    uint8_t ipcmdSerialClkFreq;      /* 0x1C8 */
    uint8_t isUniformBlockSize;      /* 0x1C9 */
    uint8_t reserved0[2];            /* 0x1CA */
    uint8_t serialNorType;           /* 0x1CC */
    uint8_t needExitNoCmdMode;       /* 0x1CD */
    uint8_t halfClkForNonReadCmd;    /* 0x1CE */
    uint8_t needRestoreNoCmdMode;    /* 0x1CF */
    uint32_t blockSize;              /* 0x1D0 */
    uint32_t reserve2[11];           /* 0x1D4 */
} flexspi_nor_config_t;              /* 512 B */

_Static_assert(sizeof(flexspi_mem_config_t) == 448, "FCB memConfig must be 448 bytes");
_Static_assert(sizeof(flexspi_nor_config_t) == 512, "FCB must be 512 bytes");
_Static_assert(__builtin_offsetof(flexspi_mem_config_t, serialClkFreq) == 0x46, "FCB layout");
_Static_assert(__builtin_offsetof(flexspi_mem_config_t, sflashA1Size) == 0x50, "FCB layout");
_Static_assert(__builtin_offsetof(flexspi_mem_config_t, lookupTable) == 0x80, "FCB layout");

/* Pre-defined ROM LUT sequence indexes for serial NOR (RM Table 9-16). Each sequence = 4 words. */
#define SEQ_READ        0
#define SEQ_READSTATUS  1
#define SEQ_WRITEENABLE 3
#define SEQ_ERASESECTOR 5
#define SEQ_ERASEBLOCK  8
#define SEQ_PAGEPROGRAM 9
#define SEQ_CHIPERASE   11

#define TK_FLASH_SIZE   (8u * 1024u * 1024u)

__attribute__((used, section(".boot_hdr.conf")))
const flexspi_nor_config_t g_flexspi_nor_config = {
    .memConfig = {
        .tag = 0x42464346u,         /* "FCFB" */
        .version = 0x56010400u,     /* V1.4.0 */
        .readSampleClkSrc = 0u,     /* internal loopback: DQS pad unconnected */
        .csHoldTime = 3u,
        .csSetupTime = 3u,
        .deviceType = 1u,           /* serial NOR */
        .sflashPadType = 4u,        /* quad */
        .serialClkFreq = 2u,        /* 50 MHz (conservative; internal loopback) */
        .sflashA1Size = TK_FLASH_SIZE,
        .lookupTable = {
            /* Fast Read Quad I/O 0xEB: 1-4-4, 24-bit addr, M7-0 + 4 dummy = 6 cycles @ 4 pads */
            [4 * SEQ_READ + 0] = LUT_SEQ(LUT_CMD_SDR, PAD1, 0xEB, LUT_RADDR_SDR, PAD4, 24),
            [4 * SEQ_READ + 1] = LUT_SEQ(LUT_DUMMY_SDR, PAD4, 6, LUT_READ_SDR, PAD4, 4),
            /* Read Status Register-1 0x05 */
            [4 * SEQ_READSTATUS] = LUT_SEQ(LUT_CMD_SDR, PAD1, 0x05, LUT_READ_SDR, PAD1, 4),
            /* Write Enable 0x06 */
            [4 * SEQ_WRITEENABLE] = LUT_SEQ(LUT_CMD_SDR, PAD1, 0x06, LUT_STOP, PAD1, 0),
            /* Sector Erase 4 KB 0x20 */
            [4 * SEQ_ERASESECTOR] = LUT_SEQ(LUT_CMD_SDR, PAD1, 0x20, LUT_RADDR_SDR, PAD1, 24),
            /* Block Erase 64 KB 0xD8 */
            [4 * SEQ_ERASEBLOCK] = LUT_SEQ(LUT_CMD_SDR, PAD1, 0xD8, LUT_RADDR_SDR, PAD1, 24),
            /* Page Program 0x02 (single, safest for ROM/flashloader) */
            [4 * SEQ_PAGEPROGRAM + 0] = LUT_SEQ(LUT_CMD_SDR, PAD1, 0x02, LUT_RADDR_SDR, PAD1, 24),
            [4 * SEQ_PAGEPROGRAM + 1] = LUT_SEQ(LUT_WRITE_SDR, PAD1, 4, LUT_STOP, PAD1, 0),
            /* Chip Erase 0x60 */
            [4 * SEQ_CHIPERASE] = LUT_SEQ(LUT_CMD_SDR, PAD1, 0x60, LUT_STOP, PAD1, 0),
        },
    },
    .pageSize = 256u,
    .sectorSize = 4u * 1024u,
    .ipcmdSerialClkFreq = 1u,       /* 30 MHz for IP commands */
    .isUniformBlockSize = 0u,
    .blockSize = 64u * 1024u,
};

/* ---- IVT + boot data (RM 9.7.1.1) ------------------------------------------------------ */
typedef struct {
    uint32_t hdr;       /* tag 0xD1, length 0x0020 (big endian), version 0x41 */
    uint32_t entry;     /* vector table address (NXP convention) */
    uint32_t reserved1;
    uint32_t dcd;       /* no DCD (no SDRAM) */
    uint32_t boot_data;
    uint32_t self;
    uint32_t csf;       /* no HAB signature yet */
    uint32_t reserved2;
} ivt_t;

typedef struct {
    uint32_t start;     /* image start: FlexSPI base */
    uint32_t size;
    uint32_t plugin;
    uint32_t placeholder;
} boot_data_t;

extern const uint32_t __vector_table[];
extern const boot_data_t g_boot_data;

__attribute__((used, section(".boot_hdr.ivt")))
const ivt_t g_image_vector_table = {
    .hdr = 0x412000D1u,
    .entry = (uint32_t)__vector_table,
    .dcd = 0u,
    .boot_data = (uint32_t)&g_boot_data,
    .self = (uint32_t)&g_image_vector_table,
    .csf = 0u,
};

__attribute__((used, section(".boot_hdr.boot_data")))
const boot_data_t g_boot_data = {
    .start = 0x60000000u,
    .size = TK_FLASH_SIZE,
    .plugin = 0u,
    .placeholder = 0xFFFFFFFFu,
};
