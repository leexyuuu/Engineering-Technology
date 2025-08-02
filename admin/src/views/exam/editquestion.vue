<template>
  <div class="app-container">
    <el-form :model="form" :rules="rules" ref="form" label-width="120px">
      <el-form-item label="题目顺序" prop="order">
        <el-input
          v-model.number="form.order"
          type="number"
          style="width: 120px"
        />
      </el-form-item>
      <el-form-item label="题目描述" prop="content">
        <el-input
          v-model="form.content"
          type="textarea"
          :autosize="{ minRows: 2, maxRows: 6 }"
        />
      </el-form-item>
      <el-form-item label="需要上传文件答题">
        <el-switch v-model="form.requires_file" />
      </el-form-item>
      
      <!-- 多文件答题设置 -->
      <el-form-item label="多文件答题设置" v-if="form.requires_file">
        <div style="margin-bottom: 16px;">
          <el-button type="primary" size="mini" @click="addRequiredFile">
            添加文件要求
          </el-button>
        </div>
        <div
          v-for="(file, idx) in form.required_files"
          :key="file.uuid"
          style="
            margin-bottom: 16px;
            border: 1px solid #eee;
            padding: 16px;
            border-radius: 4px;
          "
        >
          <el-row :gutter="16">
            <el-col :span="8">
              <el-form-item :label="'文件名称'" :prop="'required_files.' + idx + '.name'">
                <el-input v-model="file.name" placeholder="请输入文件名称" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item :label="'文件类型'" :prop="'required_files.' + idx + '.type'">
                <el-select v-model="file.type" placeholder="请选择文件类型" style="width: 100%">
                  <el-option label="PDF" value="pdf" />
                  <el-option label="Word" value="doc" />
                  <el-option label="Excel" value="xls" />
                  <el-option label="图片" value="image" />
                  <el-option label="其他" value="other" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item :label="'是否必填'">
                <el-switch v-model="file.required" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item :label="'文件说明'" :prop="'required_files.' + idx + '.description'">
            <el-input
              v-model="file.description"
              type="textarea"
              :autosize="{ minRows: 1, maxRows: 3 }"
              placeholder="请输入文件说明"
            />
          </el-form-item>
          <el-button
            type="danger"
            size="mini"
            @click="removeRequiredFile(idx)"
            style="margin-top: 8px"
          >
            删除文件要求
          </el-button>
        </div>
      </el-form-item>
      
      <!-- 资料文件设置 -->
      <el-form-item label="资料文件">
        <div style="margin-bottom: 16px;">
          <el-button type="primary" size="mini" @click="addMaterialFile">
            添加资料文件
          </el-button>
        </div>
        <div
          v-for="(file, idx) in form.material_files"
          :key="file.uuid"
          style="
            margin-bottom: 16px;
            border: 1px solid #eee;
            padding: 16px;
            border-radius: 4px;
          "
        >
          <el-row :gutter="16">
            <el-col :span="8">
              <el-form-item :label="'文件名称'" :prop="'material_files.' + idx + '.name'">
                <el-input v-model="file.name" placeholder="请输入文件名称" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item :label="'文件类型'" :prop="'material_files.' + idx + '.type'">
                <el-select v-model="file.type" placeholder="请选择文件类型" style="width: 100%">
                  <el-option label="PDF" value="pdf" />
                  <el-option label="Word" value="doc" />
                  <el-option label="Excel" value="xls" />
                  <el-option label="图片" value="image" />
                  <el-option label="其他" value="other" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item :label="'上传文件'">
                <el-upload
                  :action="uploadUrl"
                  :headers="uploadHeaders"
                  :on-success="(res) => handleMaterialFileSuccess(res, idx)"
                  :on-error="handleUploadError"
                  :show-file-list="false"
                  accept=".pdf,.doc,.docx,.xls,.xlsx,.jpg,.jpeg,.png,.gif"
                >
                  <el-button size="mini" type="primary">选择文件</el-button>
                </el-upload>
                <span v-if="file.url" style="margin-left: 8px; color: #67c23a;">
                  已上传: {{ file.originalName }}
                </span>
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item :label="'文件说明'" :prop="'material_files.' + idx + '.description'">
            <el-input
              v-model="file.description"
              type="textarea"
              :autosize="{ minRows: 1, maxRows: 3 }"
              placeholder="请输入文件说明"
            />
          </el-form-item>
          <el-button
            type="danger"
            size="mini"
            @click="removeMaterialFile(idx)"
            style="margin-top: 8px"
          >
            删除资料文件
          </el-button>
        </div>
      </el-form-item>
      <el-form-item label="子问题列表">
        <div
          v-for="(sub, idx) in form.sub_questions"
          :key="sub.uuid"
          style="
            margin-bottom: 24px;
            border: 1px solid #eee;
            padding: 16px;
            border-radius: 4px;
          "
        >
          <el-row :gutter="16">
            <el-col :span="6">
              <el-form-item
                :label="'顺序'"
                :prop="'sub_questions.' + idx + '.order'"
              >
                <el-input
                  v-model.number="sub.order"
                  type="number"
                  style="width: 80px"
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item
                :label="'内容'"
                :prop="'sub_questions.' + idx + '.content'"
              >
                <el-input
                  v-model="sub.content"
                  type="textarea"
                  :autosize="{ minRows: 1, maxRows: 3 }"
                />
              </el-form-item>
            </el-col>
            <el-col :span="6">
              <el-form-item
                :label="'类型'"
                :prop="'sub_questions.' + idx + '.question_type'"
              >
                <el-select
                  v-model="sub.question_type"
                  placeholder="请选择类型"
                  style="width: 120px"
                >
                  <el-option label="单选题" value="single_choice" />
                  <el-option label="多选题" value="multiple_choice" />
                  <el-option label="填空题" value="text" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="16">
            <el-col :span="6">
              <el-form-item
                :label="'分值'"
                :prop="'sub_questions.' + idx + '.score'"
              >
                <el-input
                  v-model.number="sub.score"
                  type="number"
                  style="width: 80px"
                />
              </el-form-item>
            </el-col>
            <el-col :span="18">
              <div
                v-if="
                  sub.question_type === 'single_choice' ||
                  sub.question_type === 'multiple_choice'
                "
              >
                <el-form-item label="选项">
                  <div
                    v-for="(opt, oidx) in sub.options"
                    :key="opt.uuid"
                    style="
                      display: flex;
                      align-items: center;
                      margin-bottom: 5px;
                    "
                  >
                    <el-input
                      v-model="opt.content"
                      placeholder="选项内容"
                      style="width: 200px"
                    />
                    <el-checkbox
                      v-model="opt.is_correct"
                      style="margin-left: 10px"
                      >正确</el-checkbox
                    >
                    <el-button type="text" @click="removeOption(idx, oidx)"
                      >删除</el-button
                    >
                  </div>
                  <el-button type="primary" size="mini" @click="addOption(idx)"
                    >添加选项</el-button
                  >
                </el-form-item>
              </div>
            </el-col>
          </el-row>
          <el-button
            type="danger"
            size="mini"
            @click="removeSubQuestion(idx)"
            style="margin-top: 8px"
            >删除子问题</el-button
          >
        </div>
        <el-button type="primary" @click="addSubQuestion">添加子问题</el-button>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="onSubmit">保存</el-button>
        <el-button @click="$router.back()">取消</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script>
import {
  fetchExamQuestion,
  createExamQuestion,
  updateExamQuestion,
} from "@/api/exam";
function uuid() {
  return "_" + Math.random().toString(36).substr(2, 9);
}
export default {
  data() {
    return {
      form: {
        order: 1,
        content: "",
        exam_id: "",
        uuid: uuid(),
        requires_file: false,
        file_description: "",
        sub_questions: [],
        required_files: [], // 多文件答题要求
        material_files: [], // 资料文件
      },
      rules: {
        content: [
          { required: true, message: "请输入题目内容", trigger: "blur" },
        ],
      },
      exam_id: null,
      question_id: null,
      uploadUrl: "/api/exam/upload-file",
      uploadHeaders: {
        Authorization: localStorage.getItem("token") || "",
      },
    };
  },
  created() {
    this.exam_id = this.$route.params.exam_id;
    this.form.exam_id = this.exam_id;
    this.question_id = this.$route.params.question_id;
    if (this.question_id) {
      fetchExamQuestion(this.exam_id, this.question_id).then((res) => {
        const data = res.data || res;
        const parsedData = JSON.parse(data.sub_questions_str);

        // 2. 验证解析结果是否为数组
        if (!Array.isArray(parsedData)) {
          this.form = {
            ...data,
            required_files: data.required_files ? JSON.parse(data.required_files) : [],
            material_files: data.material_files ? JSON.parse(data.material_files) : [],
          };
        }
        else{
          this.form = {
            ...data,
            sub_questions: parsedData,
            required_files: data.required_files ? JSON.parse(data.required_files) : [],
            material_files: data.material_files ? JSON.parse(data.material_files) : [],
          };
        }
        
      });
    }
  },
  methods: {
    addSubQuestion() {
      this.form.sub_questions.push({
        order: this.form.sub_questions.length + 1,
        content: "",
        question_type: "",
        score: 1,
        options: [],
        uuid: uuid(),
      });
    },
    removeSubQuestion(idx) {
      this.form.sub_questions.splice(idx, 1);
    },
    addOption(subIdx) {
      const sub = this.form.sub_questions[subIdx];
      if (!sub.options) this.$set(sub, "options", []);
      sub.options.push({ content: "", is_correct: false, uuid: uuid() });
    },
    removeOption(subIdx, optIdx) {
      this.form.sub_questions[subIdx].options.splice(optIdx, 1);
    },
    // 多文件答题相关方法
    addRequiredFile() {
      this.form.required_files.push({
        name: "",
        type: "pdf",
        required: true,
        description: "",
        uuid: uuid(),
      });
    },
    removeRequiredFile(idx) {
      this.form.required_files.splice(idx, 1);
    },
    // 资料文件相关方法
    addMaterialFile() {
      this.form.material_files.push({
        name: "",
        type: "pdf",
        description: "",
        url: "",
        originalName: "",
        uuid: uuid(),
      });
    },
    removeMaterialFile(idx) {
      this.form.material_files.splice(idx, 1);
    },
    handleMaterialFileSuccess(res, idx) {
      if (res.code === 20000) {
        this.form.material_files[idx].url = res.data.url;
        this.form.material_files[idx].originalName = res.data.filename;
        this.$message.success("文件上传成功");
      } else {
        this.$message.error("文件上传失败");
      }
    },
    handleUploadError() {
      this.$message.error("文件上传失败");
    },
    onSubmit() {
      this.$refs.form.validate((valid) => {
        if (!valid) return;
        // 提交时去除uuid辅助字段
        const submitData = {
          ...this.form,
          sub_questions_str: JSON.stringify(this.form.sub_questions),
          required_files: JSON.stringify(this.form.required_files),
          material_files: JSON.stringify(this.form.material_files),
        };
        submitData.sub_questions = null;
        submitData.id = null;

        const action = this.question_id
          ? updateExamQuestion(this.question_id, submitData)
          : createExamQuestion(submitData);
        action.then(() => {
          this.$message.success("保存成功");
          this.$router.push({ path: `/exam/questionlist/${this.exam_id}` });
        });
      });
    },
  },
};
</script> 