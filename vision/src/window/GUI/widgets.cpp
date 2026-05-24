//
// Created by GitHub Copilot on 2026/4/10.
//

#include "widgets.h"

namespace vision {
namespace {
template<typename TDialog>
bool file_dialog_common(const FileDialogFilterVec &filters, ocarina::fs::path &path, DWORD options, const CLSID clsid) {
    TDialog *dialog;
    if (FAILED(CoCreateInstance(clsid, nullptr, CLSCTX_ALL, IID_PPV_ARGS(&dialog)))) {
        OC_WARNING("file_dialog failure");
        return false;
    }

    if (IShellItem *shell_item;
        SUCCEEDED(SHCreateItemFromParsingName(path.parent_path().c_str(), nullptr, IID_IShellItem,
                                              reinterpret_cast<void **>(&shell_item)))) {
        dialog->SetFolder(shell_item);
        shell_item->Release();
    }

    dialog->SetOptions(options | FOS_FORCEFILESYSTEM);
    if (dialog->Show(nullptr) == S_OK) {
        if (IShellItem *item; dialog->GetResult(&item) == S_OK) {
            item->Release();
            PWSTR path_str;
            if (item->GetDisplayName(SIGDN_FILESYSPATH, &path_str) == S_OK) {
                path = path_str;
                CoTaskMemFree(path_str);
                return true;
            }
        }
    }
    return false;
}
}// namespace

bool Widgets::open_file_dialog(std::filesystem::path &path, const FileDialogFilterVec &filters) noexcept {
    return file_dialog_common<IFileOpenDialog>(filters, path, FOS_FILEMUSTEXIST, CLSID_FileOpenDialog);
}

bool Widgets::slider_floatN(const ocarina::string &label, float *val, ocarina::uint size, float min, float max) noexcept {
    switch (size) {
        case 1: return slider_float(label, val, min, max);
        case 2: return slider_float2(label, reinterpret_cast<ocarina::float2 *>(val), min, max);
        case 3: return slider_float3(label, reinterpret_cast<ocarina::float3 *>(val), min, max);
        case 4: return slider_float4(label, reinterpret_cast<ocarina::float4 *>(val), min, max);
        default: OC_ERROR("error"); return false;
    }
}

bool Widgets::colorN_edit(const ocarina::string &label, float *val, ocarina::uint size) noexcept {
    switch (size) {
        case 3: return color_edit(label, reinterpret_cast<ocarina::float3 *>(val));
        case 4: return color_edit(label, reinterpret_cast<ocarina::float4 *>(val));
        default: OC_ERROR("error"); return false;
    }
}

bool Widgets::input_floatN(const ocarina::string &label, float *val, ocarina::uint size) noexcept {
    switch (size) {
        case 1: return input_float(label, val);
        case 2: return input_float2(label, reinterpret_cast<ocarina::float2 *>(val));
        case 3: return input_float3(label, reinterpret_cast<ocarina::float3 *>(val));
        case 4: return input_float4(label, reinterpret_cast<ocarina::float4 *>(val));
        default: OC_ERROR("error"); return false;
    }
}

bool Widgets::drag_floatN(const ocarina::string &label, float *val, ocarina::uint size,
                          float speed, float min, float max, const char *fmt) noexcept {
    switch (size) {
        case 1: return drag_float(label, val, speed, min, max, fmt);
        case 2: return drag_float2(label, reinterpret_cast<ocarina::float2 *>(val), speed, min, max, fmt);
        case 3: return drag_float3(label, reinterpret_cast<ocarina::float3 *>(val), speed, min, max, fmt);
        case 4: return drag_float4(label, reinterpret_cast<ocarina::float4 *>(val), speed, min, max, fmt);
        default: OC_ERROR("error"); return false;
    }
}

}// namespace vision