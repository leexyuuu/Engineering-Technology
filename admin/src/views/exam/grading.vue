<template>
  <div class="app-container">
    <div class="header-bar">
      <h3>AI阅卷复核</h3>
      <div>
        <el-tag :type="gradingStatusType" size="medium">{{ gradingStatusText }}</el-tag>
        <span v-if="gradingData.ai_total_score != null" style="margin-left: 16px; font-size: 16px;">
          AI评分: <b>{{ gradingData.ai_total_score }}</b>
        </span>
        <span v-if="gradingData.final_total_score != null" style="margin-left: 16px; font-size: 16px; color: #E6A23C;">
          最终分数: <b>{{ gradingData.final_total_score }}</b>
        </span>
        <el-button
          type="success"
          size="small"
          style="margin-left: 16px;"
          :loading="finalizing"
          @click="handleFinalize"
        >
          确认最终成绩
        </el-button>
        <el-button size="small" @click="$router.back()">返回</el-button>
      </div>
    </div>

    <div v-loading="loading">
      <div v-for="result in gradingData.results" :key="result.id" class="question-card">
        <div class="question-header">
          <span class="question-title">题目 {{ result.question_order }}</span>
          <el-tag size="small" :type="result.status === 'reviewed' ? 'success' : ''">
            AI得分: {{ result.ai_score }} | 最终: {{ result.final_score != null ? result.final_score : '待复核' }}
          </el-tag>
        </div>

        <el-table :data="parseItemScores(result.item_scores)" border size="small" style="margin-top: 10px;">
          <el-table-column prop="item_id" label="评分项" width="80" />
          <el-table-column prop="description" label="描述" min-width="200">
            <template slot-scope="scope">
              {{ scope.row.description || scope.row.reason }}
            </template>
          </el-table-column>
          <el-table-column prop="max_score" label="满分" width="60" align="center" />
          <el-table-column label="AI得分" width="80" align="center">
            <template slot-scope="scope">
              <span :style="{ color: scope.row.needs_review ? '#E6A23C' : '#67C23A' }">
                {{ scope.row.ai_score }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="置信度" width="80" align="center">
            <template slot-scope="scope">
              <el-progress
                :percentage="Math.round(scope.row.confidence * 100)"
                :color="scope.row.confidence >= 0.8 ? '#67C23A' : '#E6A23C'"
                :stroke-width="6"
                :show-text="false"
                style="width: 60px; display: inline-block;"
              />
              <span style="font-size: 11px; margin-left: 4px;">{{ Math.round(scope.row.confidence * 100) }}%</span>
            </template>
          </el-table-column>
          <el-table-column prop="method" label="判分方式" width="100">
            <template slot-scope="scope">
              <el-tag size="mini" :type="getMethodType(scope.row.method)">{{ getMethodText(scope.row.method) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="reason" label="评分理由" min-width="250" />
          <el-table-column label="修改分数" width="120" align="center">
            <template slot-scope="scope">
              <el-input-number
                v-model="scope.row.editScore"
                :min="0"
                :max="scope.row.max_score"
                :step="1"
                size="mini"
                controls-position="right"
                style="width: 90px;"
              />
            </template>
          </el-table-column>
        </el-table>

        <div style="text-align: right; margin-top: 10px;">
          <el-button
            type="primary"
            size="small"
            :loading="result.reviewing"
            @click="handleReview(result)"
          >
            提交复核
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { fetchGradingResults, submitReview, finalizeGrading } from '@/api/exam'

export default {
  data() {
    return {
      loading: false,
      finalizing: false,
      student_exam_id: null,
      exam_id: null,
      gradingData: {
        grading_status: 'not_graded',
        ai_total_score: null,
        final_total_score: null,
        results: []
      }
    }
  },
  computed: {
    gradingStatusType() {
      const map = { 'not_graded': 'info', 'ai_grading': 'warning', 'ai_graded': '', 'reviewed': 'success' }
      return map[this.gradingData.grading_status] || 'info'
    },
    gradingStatusText() {
      const map = { 'not_graded': '未评分', 'ai_grading': 'AI评分中', 'ai_graded': '待复核', 'reviewed': '已确认' }
      return map[this.gradingData.grading_status] || '未评分'
    }
  },
  created() {
    this.exam_id = this.$route.params.exam_id
    this.student_exam_id = this.$route.params.student_exam_id
    this.fetchData()
  },
  methods: {
    fetchData() {
      this.loading = true
      fetchGradingResults(this.student_exam_id).then(res => {
        this.gradingData = res.data
        this.loading = false
      }).catch(() => { this.loading = false })
    },
    parseItemScores(itemScoresStr) {
      if (!itemScoresStr) return []
      try {
        const items = typeof itemScoresStr === 'string' ? JSON.parse(itemScoresStr) : itemScoresStr
        return items.map(item => ({
          ...item,
          editScore: item.ai_score
        }))
      } catch (e) {
        return []
      }
    },
    getMethodType(method) {
      const map = { 'ast_match': 'success', 'llm_review': '', 'llm_rubric': '', 'file_check': 'warning', 'empty_check': 'info', 'human_review': 'success', 'llm_error': 'danger', 'error': 'danger' }
      return map[method] || 'info'
    },
    getMethodText(method) {
      const map = { 'ast_match': '代码匹配', 'llm_review': 'LLM审查', 'llm_rubric': 'LLM评分', 'file_check': '文件检查', 'empty_check': '空答案', 'human_review': '人工复核', 'llm_error': 'LLM异常', 'error': '异常' }
      return map[method] || method
    },
    handleReview(result) {
      const items = this.parseItemScores(result.item_scores)
      const scoreUpdates = items.map(item => ({
        item_id: item.item_id,
        score: item.editScore != null ? item.editScore : item.ai_score
      }))

      this.$set(result, 'reviewing', true)
      submitReview({
        grading_result_id: result.id,
        score_updates: scoreUpdates
      }).then(res => {
        this.$message.success('复核提交成功')
        this.fetchData()
      }).catch(error => {
        this.$message.error('复核失败: ' + (error.message || '未知错误'))
      }).finally(() => {
        this.$set(result, 'reviewing', false)
      })
    },
    handleFinalize() {
      this.$confirm('确认锁定该学生的最终成绩？未复核的题目将以AI评分为准。', '确认', { type: 'warning' }).then(() => {
        this.finalizing = true
        finalizeGrading(this.student_exam_id).then(res => {
          this.$message.success(`最终成绩已确认: ${res.data.final_total_score}分`)
          this.fetchData()
        }).catch(error => {
          this.$message.error('确认失败: ' + (error.message || '未知错误'))
        }).finally(() => {
          this.finalizing = false
        })
      }).catch(() => {})
    }
  }
}
</script>

<style scoped>
.header-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.question-card {
  background: #fff;
  border: 1px solid #EBEEF5;
  border-radius: 4px;
  padding: 20px;
  margin-bottom: 20px;
}

.question-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.question-title {
  font-size: 16px;
  font-weight: bold;
  color: #303133;
}
</style>
