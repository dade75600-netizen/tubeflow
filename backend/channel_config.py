CHANNEL_CONFIGS = {
    "military": {
        "channel_handle": "@MilitaryDeepOps",
        "thumbnail_palette": "red_white",
        "thumbnail_add_arrow": True,
        "script_tone": "military_micro",
        "bg_contrast_boost": 1.5,
        "bg_pool": "military_combat",
        "title_formula": "dramatic_revelation",
        "video_duration_target": 9,  # 8-10 seconds micro-documentary
        "token_env_var": "YOUTUBE_TOKEN_MILITARY",
        "niche": "Military Deep Ops / Military Throwback & Tech"
    },
    "aviation": {
        "channel_handle": "@CivilAviationLords", 
        "thumbnail_palette": "yellow_white",
        "thumbnail_add_arrow": False,
        "script_tone": "aviation_documentary",
        "bg_contrast_boost": 1.3,
        "bg_pool": "aviation_dramatic",
        "title_formula": "technical_drama",
        "video_duration_target": 90, # seconds
        "token_env_var": "YOUTUBE_TOKEN_CIVIL_AVIATION",
    }
}
