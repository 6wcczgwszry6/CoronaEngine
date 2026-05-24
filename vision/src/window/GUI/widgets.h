//
// Created by GitHub Copilot on 2026/4/10.
//

#pragma once

#include <utility>

#include "decl.h"
#include "core/stl.h"
#include "math/basic_types.h"
#include "core/util/util.h"
#include "core/image/image.h"

#include <commctrl.h>
#include <commdlg.h>
#include <comutil.h>
#include <psapi.h>
#include <shellscalingapi.h>
#include <ShlObj_core.h>
#include <winioctl.h>

namespace vision {

struct FileDialogFilter {
	explicit FileDialogFilter(std::string ext_, std::string desc_ = {})
		: desc(std::move(desc_)), ext(std::move(ext_)) {}
	std::string desc;
	std::string ext;
};

using FileDialogFilterVec = std::vector<FileDialogFilter>;

enum WindowFlag {
	None = 0,
	MenuBar = 1 << 10
};

class Widgets {
private:
	Window *window_{nullptr};

public:
	explicit Widgets(Window *window = nullptr) : window_(window) {}

	virtual void push_item_width(int width) noexcept = 0;
	virtual void pop_item_width() noexcept = 0;
	virtual void begin_tool_tip() noexcept = 0;
	virtual void end_tool_tip() noexcept = 0;
	virtual void image(ocarina::uint tex_handle, ocarina::uint2 size, ocarina::float2 uv0, ocarina::float2 uv1) noexcept = 0;
	virtual void image(const ocarina::Image &image) noexcept = 0;
	virtual void image(const ocarina::ImageView &image_view) noexcept = 0;

	void adaptive_image(ocarina::uint tex_handle, ocarina::uint2 res,
						ocarina::float2 uv0 = ocarina::make_float2(0),
						ocarina::float2 uv1 = ocarina::make_float2(1.f)) {
		float ratio = res.x * 1.f / res.y;
		ocarina::uint2 size = ocarina::make_uint2(node_size().x, node_size().x / ratio);
		image(tex_handle, ocarina::min(size, res), uv0, uv1);
	}

	virtual void begin_disabled() noexcept = 0;
	virtual void end_disabled() noexcept = 0;

	template<typename Func>
	void set_enabled(bool enabled, Func func) noexcept {
		if (enabled) {
			func();
		} else {
			begin_disabled();
			func();
			end_disabled();
		}
	}

	static bool open_file_dialog(std::filesystem::path &path, const FileDialogFilterVec &filters = {}) noexcept;

	virtual ocarina::uint2 node_size() noexcept = 0;

	void image(ocarina::uint tex_handle, ocarina::uint2 size) noexcept {
		image(tex_handle, size, ocarina::make_float2(0), ocarina::make_float2(1));
	}

	[[nodiscard]] Window *window() noexcept { return window_; }
	[[nodiscard]] const Window *window() const noexcept { return window_; }

	template<typename Func>
	void use_tool_tip(Func &&func) noexcept {
		begin_tool_tip();
		func();
		end_tool_tip();
	}

	template<typename Func>
	void use_item_width(int width, Func &&func) noexcept {
		push_item_width(width);
		func();
		pop_item_width();
	}

	virtual bool push_window(const ocarina::string &label) noexcept = 0;
	virtual bool push_window(const ocarina::string &label, WindowFlag flag) noexcept = 0;
	virtual void pop_window() noexcept = 0;

	template<typename Func>
	bool use_window(const ocarina::string &label, WindowFlag flag, Func &&func) noexcept {
		bool show = push_window(label, flag);
		if (show) {
			func();
		}
		pop_window();
		return show;
	}

	template<typename Func>
	bool use_window(const ocarina::string &label, Func &&func) noexcept {
		return use_window(label, WindowFlag::None, OC_FORWARD(func));
	}

	virtual bool tree_node(const ocarina::string &label) noexcept = 0;
	virtual void tree_pop() noexcept = 0;
	virtual void push_id(char *str) noexcept = 0;
	virtual void pop_id() noexcept = 0;

	template<typename T, typename Func>
	bool use_tree(T &&label, Func &&func) noexcept {
		bool show = tree_node(OC_FORWARD(label));
		if (show) {
			func();
			tree_pop();
		}
		return show;
	}

	virtual bool folding_header(const ocarina::string &label) noexcept = 0;

	template<typename T, typename Func>
	bool use_folding_header(T &&label, Func &&func) noexcept {
		bool open = folding_header(OC_FORWARD(label));
		if (open) {
			func();
		}
		return open;
	}

	virtual bool begin_main_menu_bar() noexcept = 0;
	virtual void end_main_menu_bar() noexcept = 0;
	virtual bool begin_menu_bar() noexcept = 0;
	virtual bool begin_menu(const ocarina::string &label) noexcept = 0;
	virtual bool menu_item(const ocarina::string &label) noexcept = 0;
	virtual void end_menu() noexcept = 0;
	virtual void end_menu_bar() noexcept = 0;

	template<typename Func>
	bool use_main_menu_bar(Func &&func) noexcept {
		bool ret = begin_main_menu_bar();
		if (ret) {
			func();
			end_main_menu_bar();
		}
		return ret;
	}

	template<typename Func>
	bool use_menu_bar(Func &&func) noexcept {
		bool ret = begin_menu_bar();
		if (ret) {
			func();
			end_menu_bar();
		}
		return ret;
	}

	template<typename Func>
	bool use_menu(const ocarina::string &label, Func &&func) noexcept {
		bool ret = begin_menu(label.c_str());
		if (ret) {
			func();
			end_menu();
		}
		return ret;
	}

	virtual bool radio_button(const ocarina::string &label, bool active) noexcept = 0;

	template<typename Func>
	void use_radio_button(const ocarina::string &label, Func &&func) noexcept {
		push_window(label);
		func();
		pop_window();
	}

	virtual bool input_text(const ocarina::string &label, char *buf, size_t buf_size) noexcept = 0;
	virtual void text(const char *format, ...) noexcept = 0;
	void text(const ocarina::string &str) noexcept { text(str.c_str()); }
	virtual void text_wrapped(const char *format, ...) noexcept = 0;
	virtual bool check_box(const ocarina::string &label, bool *val) noexcept = 0;

	virtual bool slider_float(const ocarina::string &label, float *val, float min, float max) noexcept = 0;
	virtual bool slider_float2(const ocarina::string &label, ocarina::float2 *val, float min, float max) noexcept = 0;
	virtual bool slider_float3(const ocarina::string &label, ocarina::float3 *val, float min, float max) noexcept = 0;
	virtual bool slider_float4(const ocarina::string &label, ocarina::float4 *val, float min, float max) noexcept = 0;
	bool slider_floatN(const ocarina::string &label, float *val, ocarina::uint size, float min, float max) noexcept;

	virtual bool slider_int(const ocarina::string &label, int *val, int min, int max) noexcept = 0;
	virtual bool slider_int2(const ocarina::string &label, ocarina::int2 *val, int min, int max) noexcept = 0;
	virtual bool slider_int3(const ocarina::string &label, ocarina::int3 *val, int min, int max) noexcept = 0;
	virtual bool slider_int4(const ocarina::string &label, ocarina::int4 *val, int min, int max) noexcept = 0;
	virtual bool slider_uint(const ocarina::string &label, ocarina::uint *val, ocarina::uint min, ocarina::uint max) noexcept = 0;
	virtual bool slider_uint2(const ocarina::string &label, ocarina::uint2 *val, ocarina::uint min, ocarina::uint max) noexcept = 0;
	virtual bool slider_uint3(const ocarina::string &label, ocarina::uint3 *val, ocarina::uint min, ocarina::uint max) noexcept = 0;
	virtual bool slider_uint4(const ocarina::string &label, ocarina::uint4 *val, ocarina::uint min, ocarina::uint max) noexcept = 0;
	virtual bool color_edit(const ocarina::string &label, ocarina::float3 *val) noexcept = 0;
	virtual bool color_edit(const ocarina::string &label, ocarina::float4 *val) noexcept = 0;
	bool colorN_edit(const ocarina::string &label, float *val, ocarina::uint size) noexcept;
	virtual bool button(const ocarina::string &label, ocarina::uint2 size) noexcept = 0;
	virtual bool button(const ocarina::string &label) noexcept = 0;

	template<typename Func>
	bool button_click(const ocarina::string &label, Func &&func) noexcept {
		bool ret = button(label.c_str());
		if (ret) {
			func();
		}
		return ret;
	}

	virtual void same_line() noexcept = 0;
	virtual void new_line() noexcept = 0;
	virtual bool input_int(const ocarina::string &label, int *val) noexcept = 0;
	virtual bool input_int(const ocarina::string &label, int *val, int step, int step_fast) noexcept = 0;

	template<typename... Args>
	bool input_int_limit(const ocarina::string &label, int *val, int min, int max, Args &&...args) noexcept {
		int old_value = *val;
		bool dirty = input_int(label, val, OC_FORWARD(args)...);
		*val = ocarina::clamp(*val, min, max);
		return dirty && *val != old_value;
	}

	virtual bool input_int2(const ocarina::string &label, ocarina::int2 *val) noexcept = 0;
	virtual bool input_int3(const ocarina::string &label, ocarina::int3 *val) noexcept = 0;
	virtual bool input_int4(const ocarina::string &label, ocarina::int4 *val) noexcept = 0;
	virtual bool input_uint(const ocarina::string &label, ocarina::uint *val) noexcept = 0;
	virtual bool input_uint(const ocarina::string &label, ocarina::uint *val, ocarina::uint step, ocarina::uint step_fast) noexcept = 0;

	template<typename... Args>
	bool input_uint_limit(const ocarina::string &label, ocarina::uint *val, ocarina::uint min, ocarina::uint max, Args &&...args) noexcept {
		ocarina::uint old_value = *val;
		bool dirty = input_uint(label, val, OC_FORWARD(args)...);
		*val = ocarina::clamp(*val, min, max);
		return dirty && *val != old_value;
	}

	virtual bool input_uint2(const ocarina::string &label, ocarina::uint2 *val) noexcept = 0;
	virtual bool input_uint3(const ocarina::string &label, ocarina::uint3 *val) noexcept = 0;
	virtual bool input_uint4(const ocarina::string &label, ocarina::uint4 *val) noexcept = 0;
	virtual bool input_float(const ocarina::string &label, float *val) noexcept = 0;
	virtual bool input_float(const ocarina::string &label, float *val, float step, float step_fast) noexcept = 0;

	template<typename... Args>
	bool input_float_limit(const ocarina::string &label, float *val, float min, float max, Args &&...args) noexcept {
		float old_value = *val;
		bool dirty = input_float(label, val, OC_FORWARD(args)...);
		*val = ocarina::clamp(*val, min, max);
		return dirty && *val != old_value;
	}

	virtual bool input_float2(const ocarina::string &label, ocarina::float2 *val) noexcept = 0;
	virtual bool input_float3(const ocarina::string &label, ocarina::float3 *val) noexcept = 0;
	virtual bool input_float4(const ocarina::string &label, ocarina::float4 *val) noexcept = 0;
	bool input_floatN(const ocarina::string &label, float *val, ocarina::uint size) noexcept;
	virtual bool drag_int(const ocarina::string &label, int *val, float speed, int min = ocarina::neg_infinity_v<int>, int max = ocarina::pos_infinity_v<int>) noexcept = 0;
	virtual bool drag_int2(const ocarina::string &label, ocarina::int2 *val, float speed, int min = ocarina::neg_infinity_v<int>, int max = ocarina::pos_infinity_v<int>) noexcept = 0;
	virtual bool drag_int3(const ocarina::string &label, ocarina::int3 *val, float speed, int min = ocarina::neg_infinity_v<int>, int max = ocarina::pos_infinity_v<int>) noexcept = 0;
	virtual bool drag_int4(const ocarina::string &label, ocarina::int4 *val, float speed, int min = ocarina::neg_infinity_v<int>, int max = ocarina::pos_infinity_v<int>) noexcept = 0;
	virtual bool drag_uint(const ocarina::string &label, ocarina::uint *val, float speed, ocarina::uint min = ocarina::neg_infinity_v<ocarina::uint>, ocarina::uint max = ocarina::pos_infinity_v<ocarina::uint>) noexcept = 0;
	virtual bool drag_uint2(const ocarina::string &label, ocarina::uint2 *val, float speed, ocarina::uint min = ocarina::neg_infinity_v<ocarina::uint>, ocarina::uint max = ocarina::pos_infinity_v<ocarina::uint>) noexcept = 0;
	virtual bool drag_uint3(const ocarina::string &label, ocarina::uint3 *val, float speed, ocarina::uint min = ocarina::neg_infinity_v<ocarina::uint>, ocarina::uint max = ocarina::pos_infinity_v<ocarina::uint>) noexcept = 0;
	virtual bool drag_uint4(const ocarina::string &label, ocarina::uint4 *val, float speed, ocarina::uint min = ocarina::neg_infinity_v<ocarina::uint>, ocarina::uint max = ocarina::pos_infinity_v<ocarina::uint>) noexcept = 0;
	virtual bool drag_float(const ocarina::string &label, float *val, float speed, float min = ocarina::neg_infinity_v<float>, float max = ocarina::pos_infinity_v<float>, const char *fmt = "%.3f") noexcept = 0;
	virtual bool drag_float2(const ocarina::string &label, ocarina::float2 *val, float speed, float min = ocarina::neg_infinity_v<float>, float max = ocarina::pos_infinity_v<float>, const char *fmt = "%.3f") noexcept = 0;
	virtual bool drag_float3(const ocarina::string &label, ocarina::float3 *val, float speed, float min = ocarina::neg_infinity_v<float>, float max = ocarina::pos_infinity_v<float>, const char *fmt = "%.3f") noexcept = 0;
	virtual bool drag_float4(const ocarina::string &label, ocarina::float4 *val, float speed, float min = ocarina::neg_infinity_v<float>, float max = ocarina::pos_infinity_v<float>, const char *fmt = "%.3f") noexcept = 0;
	bool drag_floatN(const ocarina::string &label, float *val, ocarina::uint size, float speed = 0.1f, float min = 0, float max = 0, const char *fmt = "%.3f") noexcept;
	virtual bool combo(const ocarina::string &label, int *current_item, const char *const items[], int item_num) noexcept = 0;
	virtual bool is_item_hovered() noexcept = 0;
	virtual ocarina::float2 mouse_pos() noexcept = 0;

	bool combo(const ocarina::string &label, int *current_item, const ocarina::vector<const char *> &items) noexcept {
		return combo(label, current_item, items.data(), items.size());
	}

	template<size_t N>
	bool combo(const ocarina::string &label, int *current_item, const ocarina::array<const char *, N> &items) noexcept {
		return combo(label, current_item, items.data(), items.size());
	}

	virtual ~Widgets() = default;
};

}// namespace vision