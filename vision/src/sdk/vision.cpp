//
// Created by Zero on 2023/7/17.
//

#ifndef VISION_SDK_EXPORT_DLL
#define VISION_SDK_EXPORT_DLL 1
#endif

#include "vision.h"

uint32_t vision_sdk_abi_version(void) noexcept {
	return VISION_SDK_ABI_VERSION;
}

const char *vision_sdk_name(void) noexcept {
	return "vision-renderer";
}

