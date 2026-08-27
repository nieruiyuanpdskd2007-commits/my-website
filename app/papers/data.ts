export type Paper = {
  id: string;
  title: string;
  year: number;
  venue: string;
  topic: string;
  status: "已读" | "阅读中" | "待读";
  source: "本地 PDF" | "推荐";
  analysis?: boolean;
  reason?: string;
  match?: number;
};

export const libraryPapers: Paper[] = [
  { id: "bloomberggpt", title: "BloombergGPT: A Large Language Model for Finance", year: 2023, venue: "arXiv", topic: "领域大模型", status: "已读", source: "本地 PDF", analysis: true },
  { id: "occworld", title: "OccWorld: Learning a 3D Occupancy World Model for Autonomous Driving", year: 2023, venue: "arXiv", topic: "世界模型", status: "已读", source: "本地 PDF", analysis: true },
  { id: "tram", title: "TRAM: Global Trajectory and Motion of 3D Humans from In-the-Wild Videos", year: 2024, venue: "ECCV", topic: "人体运动恢复", status: "已读", source: "本地 PDF", analysis: true },
  { id: "wham", title: "WHAM: Reconstructing World-grounded Humans with Accurate 3D Motion", year: 2024, venue: "CVPR", topic: "人体运动恢复", status: "已读", source: "本地 PDF", analysis: true },
  { id: "gvhmr", title: "World-Grounded Human Motion Recovery via Gravity-View Coordinates", year: 2024, venue: "SIGGRAPH Asia", topic: "人体运动恢复", status: "已读", source: "本地 PDF", analysis: true },
  { id: "retargeting", title: "Retargeting Matters: General Motion Retargeting for Humanoid Robots", year: 2025, venue: "arXiv", topic: "人形机器人", status: "阅读中", source: "本地 PDF", analysis: true },
  { id: "diffproxy", title: "DiffProxy: Diffusion as Proxy for Multi-view Human Mesh Recovery", year: 2026, venue: "arXiv", topic: "人体网格恢复", status: "待读", source: "本地 PDF", analysis: true },
  { id: "nmr", title: "NMR: Neural Motion Retargeting for Humanoid Control", year: 2026, venue: "arXiv", topic: "人形机器人", status: "待读", source: "本地 PDF", analysis: true },
  { id: "omnifit", title: "OmniFit: Unified 3D Human Asset Fitting", year: 2026, venue: "arXiv", topic: "人体网格恢复", status: "待读", source: "本地 PDF", analysis: true },
  { id: "videoworld", title: "VideoWorld: Exploring Knowledge Learning from Unlabeled Videos", year: 2025, venue: "CVPR", topic: "视频世界模型", status: "已读", source: "本地 PDF", analysis: true },
  { id: "videoworld2", title: "VideoWorld 2: Learning Transferable Knowledge from Real-world Videos", year: 2026, venue: "CVPR", topic: "视频世界模型", status: "阅读中", source: "本地 PDF", analysis: true },
];

export const recommendedPapers: Paper[] = [
  { id: "genie", title: "Genie: Generative Interactive Environments", year: 2024, venue: "ICML", topic: "视频世界模型", status: "待读", source: "推荐", match: 94, reason: "与你关注的 VideoWorld 主线高度相关：从无动作标签视频中学习可控的潜动作空间。" },
  { id: "lapo", title: "Learning to Act without Actions", year: 2024, venue: "ICLR Spotlight", topic: "潜动作学习", status: "待读", source: "推荐", match: 93, reason: "潜动作预训练的基础方案，可以帮助你建立 VideoWorld 与 LAPA 之间的方法演进脉络。" },
  { id: "dinowm", title: "DINO-WM: World Models on Pre-trained Visual Features", year: 2025, venue: "ICML", topic: "视觉规划", status: "待读", source: "推荐", match: 91, reason: "使用预训练视觉特征进行世界建模，适合继续探索非像素空间的规划与控制。" },
  { id: "lapa", title: "Latent Action Pretraining from Videos", year: 2025, venue: "ICLR", topic: "潜动作学习", status: "待读", source: "推荐", match: 90, reason: "把无标签视频中的潜动作表征迁移到视觉—语言—动作模型，与你的视频学习兴趣直接相连。" },
  { id: "dreamerv3", title: "Mastering Diverse Control Tasks through World Models", year: 2025, venue: "Nature", topic: "世界模型", status: "待读", source: "推荐", match: 86, reason: "提供通用且稳健的想象式控制基线，适合作为世界模型方向的方法论参照。" },
  { id: "tokenhmr", title: "TokenHMR: Advancing Human Mesh Recovery with a Tokenized Pose Representation", year: 2024, venue: "CVPR", topic: "人体网格恢复", status: "待读", source: "推荐", match: 89, reason: "离散姿态先验与损失偏差修正，可以补充你已有 WHAM、TRAM 与 GVHMR 的阅读链。" },
  { id: "prompthmr", title: "PromptHMR: Promptable Human Mesh Recovery", year: 2025, venue: "CVPR", topic: "人体网格恢复", status: "待读", source: "推荐", match: 88, reason: "通过空间与语义提示统一多人、交互和视频恢复，是已有 HMR 阅读线的自然延伸。" },
  { id: "proxycap", title: "ProxyCap: Real-time Monocular Full-body Capture in World Space", year: 2024, venue: "CVPR", topic: "人体运动恢复", status: "待读", source: "推荐", match: 87, reason: "实时且不依赖 SLAM 的世界坐标全身捕捉，与 WHAM 的工程取舍形成很好的对照。" },
  { id: "humanplus", title: "HumanPlus: Humanoid Shadowing and Imitation from Humans", year: 2024, venue: "CoRL", topic: "人形机器人", status: "待读", source: "推荐", match: 85, reason: "从人类动作到人形机器人自主技能的全栈系统，可连接动作恢复与机器人控制两条主线。" },
  { id: "omnih2o", title: "OmniH2O: Universal and Dexterous Human-to-Humanoid Whole-Body Teleoperation", year: 2024, venue: "CoRL", topic: "人形机器人", status: "待读", source: "推荐", match: 84, reason: "以稀疏姿态接口连接遥操作、模仿学习和自主控制，适合作为动作迁移方向的系统性案例。" },
];
